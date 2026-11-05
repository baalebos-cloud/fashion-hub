"""Uber/InDrive-style dispatch on top of the internal courier flow, plus a
logistics-style delivery journey.

- Riders see priced job cards (fare, approximate road distance, pickup and
  drop-off *areas*), never exact addresses or contacts before assignment.
- A rider can claim at the suggested fare, or make one offer (own fare within
  80-200% of suggested, plus minutes to pickup). Offers expire.
- The order's seller compares offers with rider cards and accepts one; the
  same locked assignment path as instant claims is used.
- The journey merges order and delivery milestones with timestamps, and an
  approximate ETA from the rider's live GPS while in transit.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.timezone import utcnow
from app.models.delivery import Delivery
from app.models.delivery_offer import DeliveryOffer
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.location import Location
from app.models.notification import Notification
from app.models.order import Order
from app.models.user import User
from app.services.dispatch_pricing import eta_minutes, offer_bounds, road_km, suggested_fare
from app.services.dispatch_routing import estimate_straight_line_km, validate_point
from app.services.internal_courier_service import REQUESTABLE, InternalCourierService


def _point(location: Location | None):
    if location is None:
        return None
    try:
        return validate_point(location.latitude, location.longitude)
    except Exception:  # noqa: BLE001 - corrupt pins are treated as unknown.
        return None


def _area(location: Location | None) -> str | None:
    if location is None:
        return None
    parts = [p for p in (location.city, location.state_region) if p]
    return ", ".join(dict.fromkeys(parts)) or None


def _first_name(user: User | None) -> str:
    return ((user.full_name or "").strip().split(" ")[0] if user else "") or "Rider"


class DispatchMarketplaceService:
    def __init__(self, db: Session):
        self.db = db
        self.courier = InternalCourierService(db)

    # ---- shared helpers ------------------------------------------------
    def _route(self, request: DeliveryRequest):
        pickup = self.db.get(Location, request.pickup_location_id)
        dropoff = self.db.get(Location, request.dropoff_location_id)
        km = estimate_straight_line_km(_point(pickup), _point(dropoff))
        return pickup, dropoff, km

    def _fare(self, request: DeliveryRequest, km) -> Decimal:
        if request.proposed_fee and Decimal(str(request.proposed_fee)) > 0:
            return Decimal(str(request.proposed_fee))
        return suggested_fare(km)

    def _rider_card(self, partner: DeliveryPartner) -> dict:
        user = self.db.get(User, partner.user_id)
        completed = self.db.query(func.count(Delivery.id)).filter(
            Delivery.delivery_partner_id == partner.id, Delivery.status == "delivered").scalar() or 0
        return {"first_name": _first_name(user), "is_verified": bool(partner.is_verified),
                "rating": float(partner.average_rating or 0), "vehicle_type": partner.vehicle_type,
                "completed_deliveries": int(completed),
                "photo_url": user.profile_photo_url if user else None}

    def _expire_stale(self, request_id=None):
        query = self.db.query(DeliveryOffer).filter(DeliveryOffer.status == "pending",
                                                    DeliveryOffer.expires_at < utcnow())
        if request_id is not None:
            query = query.filter(DeliveryOffer.delivery_request_id == request_id)
        changed = query.update({DeliveryOffer.status: "declined"}, synchronize_session=False)
        if changed:
            self.db.commit()

    # ---- rider side ----------------------------------------------------
    def job_board(self, *, actor, limit=20) -> list[dict]:
        requests = self.courier.list_available(actor=actor, limit=limit)
        partner = self.db.query(DeliveryPartner).filter_by(user_id=actor.id).first()
        self._expire_stale()
        jobs = []
        for request in requests:
            pickup, dropoff, km = self._route(request)
            fare = self._fare(request, km)
            low, high = offer_bounds(fare)
            mine = (self.db.query(DeliveryOffer).filter_by(delivery_request_id=request.id,
                                                          delivery_partner_id=partner.id).first()
                    if partner else None)
            jobs.append({
                "id": request.id, "order_id": request.order_id, "status": request.status,
                "suggested_fare": float(fare), "currency": "NGN",
                "offer_min": float(low), "offer_max": float(high),
                "approx_road_km": road_km(km),
                "pickup_area": _area(pickup), "dropoff_area": _area(dropoff),
                "posted_at": request.created_at,
                "my_offer": ({"id": mine.id, "amount": float(mine.amount), "status": mine.status,
                              "eta_to_pickup_minutes": mine.eta_to_pickup_minutes,
                              "expires_at": mine.expires_at} if mine else None),
            })
        return jobs

    def make_offer(self, *, request_id, actor, amount: Decimal, eta_to_pickup_minutes: int) -> DeliveryOffer:
        partner = self.courier._verified_available_partner(actor)
        request = self.db.get(DeliveryRequest, request_id)
        order = self.db.get(Order, request.order_id) if request else None
        if not request or request.status != "requested" or not order or order.status not in REQUESTABLE:
            raise NotFoundError("Available delivery request not found.")
        _, _, km = self._route(request)
        low, high = offer_bounds(self._fare(request, km))
        if not (low <= amount <= high):
            raise ValidationAppError(f"Offer between ₦{low:,.0f} and ₦{high:,.0f}.")
        if not 1 <= eta_to_pickup_minutes <= 120:
            raise ValidationAppError("Minutes to pickup must be between 1 and 120.")
        offer = self.db.query(DeliveryOffer).filter_by(delivery_request_id=request.id,
                                                       delivery_partner_id=partner.id).first()
        if offer is None:
            offer = DeliveryOffer(delivery_request_id=request.id, delivery_partner_id=partner.id)
            self.db.add(offer)
        elif offer.status == "accepted":
            raise ConflictError("Your offer was already accepted.")
        offer.amount = amount
        offer.eta_to_pickup_minutes = eta_to_pickup_minutes
        offer.status = "pending"
        offer.expires_at = utcnow() + timedelta(minutes=settings.DISPATCH_OFFER_TTL_MINUTES)
        self.db.add(Notification(
            recipient_user_id=order.seller_user_id, channel="in_app", event_type="dispatch.offer",
            title="New delivery offer",
            body=f"A rider offered ₦{amount:,.0f} to deliver order {order.order_number}.",
        ))
        self.db.commit()
        self.db.refresh(offer)
        return offer

    def withdraw_offer(self, *, request_id, actor) -> None:
        partner = self.db.query(DeliveryPartner).filter_by(user_id=actor.id).first()
        offer = (self.db.query(DeliveryOffer).filter_by(delivery_request_id=request_id,
                                                       delivery_partner_id=partner.id).first()
                 if partner else None)
        if offer is None or offer.status != "pending":
            raise NotFoundError("No pending offer to withdraw.")
        offer.status = "withdrawn"
        self.db.commit()

    # ---- seller side ---------------------------------------------------
    def _seller_request(self, *, order_id, actor):
        order = self.db.get(Order, order_id)
        if not order or str(order.seller_user_id) != str(actor.id):
            raise NotFoundError("Order not found.")
        request = (self.db.query(DeliveryRequest).filter_by(order_id=order.id)
                   .order_by(DeliveryRequest.created_at.desc()).first())
        return order, request

    def seller_dispatch(self, *, order_id, actor) -> dict:
        order, request = self._seller_request(order_id=order_id, actor=actor)
        if request is None:
            return {"request": None, "offers": []}
        self._expire_stale(request.id)
        _, _, km = self._route(request)
        offers = (self.db.query(DeliveryOffer)
                  .filter(DeliveryOffer.delivery_request_id == request.id, DeliveryOffer.status == "pending")
                  .order_by(DeliveryOffer.amount, DeliveryOffer.eta_to_pickup_minutes).all())
        cards = []
        for offer in offers:
            partner = self.db.get(DeliveryPartner, offer.delivery_partner_id)
            if partner is None:
                continue
            cards.append({"id": offer.id, "amount": float(offer.amount),
                          "eta_to_pickup_minutes": offer.eta_to_pickup_minutes,
                          "expires_at": offer.expires_at, "rider": self._rider_card(partner)})
        return {"request": {"id": request.id, "status": request.status,
                            "suggested_fare": float(self._fare(request, km)),
                            "approx_road_km": road_km(km), "currency": "NGN"},
                "offers": cards}

    def accept_offer(self, *, offer_id, actor) -> Delivery:
        offer = self.db.get(DeliveryOffer, offer_id)
        if offer is None:
            raise NotFoundError("Offer not found.")
        request = (self.db.query(DeliveryRequest).filter_by(id=offer.delivery_request_id)
                   .with_for_update().populate_existing().first())
        order = self.db.get(Order, request.order_id) if request else None
        if not order or str(order.seller_user_id) != str(actor.id):
            raise NotFoundError("Offer not found.")
        if request.status != "requested" or order.status not in REQUESTABLE:
            raise ConflictError("This delivery already has a rider.")
        offer = (self.db.query(DeliveryOffer).filter_by(id=offer_id)
                 .with_for_update().populate_existing().first())
        if offer.status != "pending" or offer.expires_at < utcnow():
            raise ConflictError("This offer has expired. Choose another or wait for new offers.")
        partner = (self.db.query(DeliveryPartner).filter_by(id=offer.delivery_partner_id)
                   .with_for_update().populate_existing().first())
        if not partner or not partner.is_verified or not partner.is_available:
            offer.status = "declined"
            self.db.commit()
            raise ConflictError("That rider is no longer available. Choose another offer.")
        delivery = self.courier.assign(request=request, order=order, partner=partner,
                                       fee=offer.amount, accepted_offer_id=offer.id)
        self.db.add(Notification(
            recipient_user_id=partner.user_id, channel="in_app", event_type="dispatch.offer_accepted",
            title="Your offer was accepted",
            body=f"Head to pickup for order {order.order_number}. Fare: ₦{Decimal(str(offer.amount)):,.0f}.",
        ))
        self.db.commit()
        return delivery

    # ---- journey -------------------------------------------------------
    def journey(self, *, order_id, actor) -> dict:
        order = self.db.get(Order, order_id)
        if order is None:
            raise NotFoundError("Order not found.")
        delivery = (self.db.query(Delivery).filter(Delivery.order_id == order.id)
                    .order_by(Delivery.created_at.desc()).first())
        partner = self.db.get(DeliveryPartner, delivery.delivery_partner_id) if delivery and delivery.delivery_partner_id else None
        is_party = (actor.role == "admin"
                    or str(actor.id) in {str(order.buyer_user_id), str(order.seller_user_id)}
                    or (partner is not None and str(partner.user_id) == str(actor.id)))
        if not is_party:
            raise NotFoundError("Order not found.")

        request = self.db.get(DeliveryRequest, delivery.delivery_request_id) if delivery else (
            self.db.query(DeliveryRequest).filter_by(order_id=order.id)
            .order_by(DeliveryRequest.created_at.desc()).first())
        rider_user = self.db.get(User, partner.user_id) if partner else None
        steps = [
            ("placed", "Order placed", order.ordered_at or order.created_at),
            ("paid", "Payment confirmed", order.paid_at),
            ("accepted", "Accepted by your tailor", order.accepted_at),
            ("in_production", "Being made", order.production_started_at),
            ("ready", "Ready for pickup", order.ready_at),
            ("dispatch_requested", "Looking for a rider", request.created_at if request else None),
            ("rider_assigned", f"Rider assigned: {_first_name(rider_user)}" if partner else "Rider assigned",
             delivery.created_at if delivery else None),
            ("picked_up", "Picked up by rider", delivery.picked_up_at if delivery else None),
            ("delivered", "Delivered", (delivery.delivered_at if delivery else None) or order.delivered_at),
            ("received", "Received and confirmed", order.received_at),
        ]
        if order.order_type == "vendor_order":
            steps = [s for s in steps if s[0] not in {"accepted", "in_production"}]
        if order.status in {"cancelled", "refunded", "rejected"}:
            steps.append(("cancelled", "Order " + order.status, order.cancelled_at))

        milestones, current_found = [], False
        last_done = max((i for i, s in enumerate(steps) if s[2] is not None), default=-1)
        for index, (key, label, at) in enumerate(steps):
            if index <= last_done:
                state = "done"  # earlier steps without a timestamp still happened
            elif not current_found:
                state, current_found = "current", True
            else:
                state = "upcoming"
            milestones.append({"key": key, "label": label, "at": at, "state": state})

        live = None
        if delivery and delivery.status == "in_transit":
            from app.services.delivery_position import read_position
            position = read_position(delivery.id)
            dropoff = self.db.get(Location, request.dropoff_location_id) if request else None
            if position and _point(dropoff):
                km = estimate_straight_line_km(
                    {"latitude": float(position["latitude"]), "longitude": float(position["longitude"])},
                    _point(dropoff))
                live = {"eta_minutes": eta_minutes(km, partner.vehicle_type if partner else None),
                        "distance_remaining_km": road_km(km), "basis": "live_gps_estimate",
                        "updated_at": position.get("recorded_at")}
        return {"order_id": order.id, "tracking_number": order.order_number,
                "status": order.status, "delivery_status": delivery.status if delivery else None,
                "milestones": milestones, "live": live}
