"""Dispatcher control tower: exceptions that need a person, and how dispatch is performing.

Every rule is deterministic and its thresholds are settings, so an alert can always be
explained. Read-only: nothing here changes a delivery. Coordinates never leave this module;
only distances and states do.

Exceptions
  unassigned_too_long  a job waiting for a rider longer than DISPATCH_ALERT_UNASSIGNED_MIN
  pickup_delayed       assigned but not collected after DISPATCH_ALERT_PICKUP_MIN
  dropoff_delayed      collected and still travelling well past the route's expected time
  tracking_lost        travelling, but no live or recent location for a while
  location_off         the rider's phone says location permission is off
  off_route            the rider is much further from the drop-off than the whole trip is long
  rider_issue          an open rider issue report
"""
from __future__ import annotations

from datetime import timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timezone import utcnow
from app.models.delivery import Delivery
from app.models.delivery_issue import DispatchIssueReport
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.dispatch_job_offer import DispatchJobOffer
from app.models.location import Location
from app.models.order import Order
from app.models.user import User
from app.services.dispatch_routing import estimate_straight_line_km, validate_point

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}
ACTIVE = ("assigned", "picked_up", "in_transit", "out_for_delivery")


def _aware(value):
    return value if value is None or value.tzinfo else value.replace(tzinfo=timezone.utc)


def _minutes_since(value, now) -> int | None:
    value = _aware(value)
    return None if value is None else max(0, int((now - value).total_seconds() // 60))


def _duration(minutes: int | None) -> str:
    """'45 min', '2 h 5 min', '1 day 3 h' — long waits read better in hours."""
    if minutes is None:
        return "an unknown time"
    if minutes < 120:
        return f"{minutes} min"
    hours, mins = divmod(minutes, 60)
    if hours < 48:
        return f"{hours} h {mins} min" if mins else f"{hours} h"
    days, hours = divmod(hours, 24)
    return f"{days} days {hours} h" if hours else f"{days} days"


def _point(location):
    try:
        return validate_point(location.latitude, location.longitude) if location else None
    except Exception:  # noqa: BLE001
        return None


def _first(user):
    return ((user.full_name or "").strip().split(" ") or ["Rider"])[0] if user else None


class ControlTowerService:
    def __init__(self, db: Session):
        self.db = db

    def exceptions(self, limit: int = 100) -> list[dict]:
        now = utcnow()
        alerts: list[dict] = []
        orders: dict = {}

        def order_number(order_id):
            if order_id not in orders:
                orders[order_id] = self.db.get(Order, order_id)
            return orders[order_id].order_number if orders[order_id] else None

        # Jobs nobody has taken.
        cutoff = now - timedelta(minutes=settings.DISPATCH_ALERT_UNASSIGNED_MIN)
        for request in (self.db.query(DeliveryRequest).filter(DeliveryRequest.status == "requested",
                                                              DeliveryRequest.created_at <= cutoff)
                        .order_by(DeliveryRequest.created_at).limit(limit)):
            waited = _minutes_since(request.created_at, now)
            alerts.append({"type": "unassigned_too_long", "severity": "critical" if waited >= 2 * settings.DISPATCH_ALERT_UNASSIGNED_MIN else "warning",
                           "request_id": str(request.id), "delivery_id": None, "order_number": order_number(request.order_id),
                           "rider": None, "minutes": waited,
                           "message": f"No rider for {_duration(waited)}.",
                           "action": "Open Suggested riders and assign, or check the fare."})

        active = (self.db.query(Delivery).filter(Delivery.status.in_(ACTIVE))
                  .order_by(Delivery.created_at).limit(200).all())
        partners = {p.id: (p, u) for p, u in self.db.query(DeliveryPartner, User)
                    .join(User, User.id == DeliveryPartner.user_id)
                    .filter(DeliveryPartner.id.in_([d.delivery_partner_id for d in active if d.delivery_partner_id])).all()} if active else {}
        from app.services.delivery_position import read_position, tracking_status
        for delivery in active:
            rider = _first(partners.get(delivery.delivery_partner_id, (None, None))[1])
            base = {"request_id": str(delivery.delivery_request_id), "delivery_id": str(delivery.id),
                    "order_number": order_number(delivery.order_id), "rider": rider}
            if delivery.status == "assigned":
                waited = _minutes_since(delivery.created_at, now)
                if waited is not None and waited >= settings.DISPATCH_ALERT_PICKUP_MIN:
                    alerts.append({**base, "type": "pickup_delayed",
                                   "severity": "critical" if waited >= 2 * settings.DISPATCH_ALERT_PICKUP_MIN else "warning",
                                   "minutes": waited, "message": f"Assigned {_duration(waited)} ago and not collected yet.",
                                   "action": "Call the rider; release or reassign if they can't make it."})
                continue
            # Travelling.
            request = self.db.get(DeliveryRequest, delivery.delivery_request_id)
            travelling = _minutes_since(delivery.picked_up_at, now)
            expected = (request.route_duration_minutes if request and request.route_duration_minutes else None)
            limit_min = (round(expected * settings.DISPATCH_ALERT_DROPOFF_FACTOR) + settings.DISPATCH_ALERT_DROPOFF_GRACE_MIN
                         if expected else settings.DISPATCH_ALERT_DROPOFF_MIN)
            if travelling is not None and travelling >= limit_min:
                alerts.append({**base, "type": "dropoff_delayed",
                               "severity": "critical" if travelling >= 2 * limit_min else "warning",
                               "minutes": travelling,
                               "message": (f"On the road {_duration(travelling)}; expected about {expected} min."
                                           if expected else f"On the road {_duration(travelling)}."),
                               "action": "Check the rider's location and call them or the customer."})
            status = tracking_status(delivery.id)
            if status["state"] == "permission_denied":
                alerts.append({**base, "type": "location_off", "severity": "warning", "minutes": None,
                               "message": "The rider's phone has location switched off.",
                               "action": "Ask the rider to allow location for the Tailora page."})
            elif status["state"] in {"last_known", "not_sharing", "unavailable"} and travelling is not None \
                    and travelling >= settings.DISPATCH_ALERT_TRACKING_MIN:
                alerts.append({**base, "type": "tracking_lost", "severity": "warning",
                               "minutes": status["age_seconds"] // 60 if status["age_seconds"] else None,
                               "message": ("No live location; last seen "
                                           f"{_duration(status['age_seconds'] // 60)} ago." if status["age_seconds"]
                                           else "The rider isn't sharing their location."),
                               "action": "Ask the rider to keep the delivery page open and sharing."})
            position = read_position(delivery.id)
            if position and position.get("freshness") in {"live", "delayed"} and request:
                pickup = _point(self.db.get(Location, request.pickup_location_id))
                dropoff = _point(self.db.get(Location, request.dropoff_location_id))
                here = {"latitude": float(position["latitude"]), "longitude": float(position["longitude"])}
                trip = estimate_straight_line_km(pickup, dropoff) if pickup and dropoff else None
                remaining = estimate_straight_line_km(here, dropoff) if dropoff else None
                if trip is not None and remaining is not None and remaining > trip + settings.DISPATCH_ALERT_OFF_ROUTE_KM:
                    alerts.append({**base, "type": "off_route", "severity": "warning", "minutes": None,
                                   "message": f"{remaining:.1f} km from the drop-off; the whole trip is {trip:.1f} km.",
                                   "action": "Call the rider to confirm where they are going."})
        # Open rider issues.
        for issue, delivery in (self.db.query(DispatchIssueReport, Delivery)
                                .join(Delivery, Delivery.id == DispatchIssueReport.delivery_id)
                                .filter(DispatchIssueReport.status.notin_(("RESOLVED", "REROUTED")))
                                .order_by(DispatchIssueReport.created_at).limit(limit)):
            alerts.append({"type": "rider_issue", "severity": "critical" if issue.status == "OPEN" else "info",
                           "request_id": str(delivery.delivery_request_id), "delivery_id": str(delivery.id),
                           "order_number": order_number(delivery.order_id),
                           "rider": _first(partners.get(delivery.delivery_partner_id, (None, None))[1]),
                           "minutes": _minutes_since(issue.created_at, now),
                           "message": f"Rider reported: {issue.issue_type.replace('_', ' ').lower()}.",
                           "action": "Open Rider issues to investigate."})
        alerts.sort(key=lambda a: (SEVERITY_ORDER[a["severity"]], -(a["minutes"] or 0)))
        return alerts[:limit]

    def performance(self) -> dict:
        """Today's dispatch numbers (UTC day). Medians are robust to one very slow delivery."""
        now = utcnow()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        requested = self.db.query(func.count(DeliveryRequest.id)).filter(DeliveryRequest.created_at >= start).scalar() or 0
        assigned = self.db.query(func.count(DeliveryRequest.id)).filter(
            DeliveryRequest.created_at >= start, DeliveryRequest.status == "assigned").scalar() or 0
        delivered = self.db.query(Delivery).filter(Delivery.delivered_at.is_not(None), Delivery.delivered_at >= start.replace(tzinfo=None)).all()
        assign_minutes, pickup_minutes, trip_minutes = [], [], []
        for d in delivered:
            req = self.db.get(DeliveryRequest, d.delivery_request_id)
            if req and d.created_at and req.created_at:
                assign_minutes.append((_aware(d.created_at) - _aware(req.created_at)).total_seconds() / 60)
            if d.picked_up_at and d.created_at:
                pickup_minutes.append((_aware(d.picked_up_at) - _aware(d.created_at)).total_seconds() / 60)
            if d.delivered_at and d.picked_up_at:
                trip_minutes.append((_aware(d.delivered_at) - _aware(d.picked_up_at)).total_seconds() / 60)
        offers = dict(self.db.query(DispatchJobOffer.status, func.count(DispatchJobOffer.id))
                      .filter(DispatchJobOffer.created_at >= start).group_by(DispatchJobOffer.status).all())
        answered = sum(offers.get(s, 0) for s in ("accepted", "declined", "expired"))

        def median(values):
            if not values:
                return None
            ordered = sorted(values)
            mid = len(ordered) // 2
            return round(ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2)

        return {"since": start.isoformat(), "jobs_requested": requested, "jobs_assigned_waiting_or_active": assigned,
                "delivered": len(delivered), "median_minutes_to_assign": median(assign_minutes),
                "median_minutes_to_pickup": median(pickup_minutes), "median_trip_minutes": median(trip_minutes),
                "auto_offer_acceptance": round(offers.get("accepted", 0) / answered, 2) if answered else None,
                "auto_offers_answered": answered}

    def riders(self) -> list[dict]:
        """Every verified rider with what they're doing now (no coordinates)."""
        from app.services.delivery_position import tracking_status
        rows = (self.db.query(DeliveryPartner, User).join(User, User.id == DeliveryPartner.user_id)
                .filter(DeliveryPartner.is_verified.is_(True), User.is_active.is_(True))
                .order_by(DeliveryPartner.is_available.desc(), User.full_name).limit(200).all())
        active = {}
        for d in self.db.query(Delivery).filter(Delivery.status.in_(ACTIVE),
                                                Delivery.delivery_partner_id.in_([p.id for p, _ in rows])).all():
            active.setdefault(d.delivery_partner_id, []).append(d)
        result = []
        for partner, user in rows:
            jobs = active.get(partner.id, [])
            travelling = next((d for d in jobs if d.status == "in_transit"), None)
            state = "on_delivery" if jobs else ("online" if partner.is_available else "offline")
            result.append({"id": str(partner.id), "first_name": _first(user), "vehicle_type": partner.vehicle_type,
                           "rating": float(partner.average_rating or 0), "state": state, "active_jobs": len(jobs),
                           "tracking": tracking_status(travelling.id) if travelling else None})
        return result
