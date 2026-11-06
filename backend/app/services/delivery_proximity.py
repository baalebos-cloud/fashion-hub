"""Buyer alerts from the rider's shared GPS: "about N min away" and "has arrived".

Each alert fires at most once per delivery run. A Redis SET NX key makes that atomic
across API workers; the delivery event log records what was sent. Alerts never block
or fail the rider's position update, and never reveal the rider's coordinates.
"""
from __future__ import annotations

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.location import Location
from app.models.notification import Notification
from app.models.order import Order
from app.services.delivery_handover import record_event
from app.services.dispatch_pricing import eta_minutes
from app.services.dispatch_routing import estimate_straight_line_km, validate_point

logger = get_logger(__name__)
ALERT_KEY_TTL_SECONDS = 12 * 3600
MAX_ARRIVAL_ACCURACY_M = 100


def _stage(km: float, accuracy_m: float, vehicle: str | None) -> tuple[str | None, int | None]:
    eta = eta_minutes(km, vehicle)
    if km * 1000 <= settings.DELIVERY_ARRIVAL_RADIUS_M and accuracy_m <= MAX_ARRIVAL_ACCURACY_M:
        return "arrived", eta
    if eta is not None and eta <= settings.DELIVERY_APPROACH_ALERT_MINUTES:
        return "approaching", eta
    return None, eta


def _claim(delivery_id, stage: str) -> bool:
    """True only for the first caller to reach this stage on this run."""
    redis = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
    return bool(redis.set(f"delivery:alert:{delivery_id}:{stage}", "1", nx=True, ex=ALERT_KEY_TTL_SECONDS))


def check_proximity(db: Session, delivery: Delivery, *, latitude: float, longitude: float, accuracy_m: float) -> str | None:
    """Send the next proximity alert if the rider just crossed a threshold. Returns the stage sent."""
    if not settings.DELIVERY_PROXIMITY_ALERTS_ENABLED or delivery.status != "in_transit":
        return None
    try:
        request = db.get(DeliveryRequest, delivery.delivery_request_id)
        dropoff = db.get(Location, request.dropoff_location_id) if request else None
        target = validate_point(dropoff.latitude, dropoff.longitude) if dropoff else None
        if target is None:
            return None
        partner = db.get(DeliveryPartner, delivery.delivery_partner_id) if delivery.delivery_partner_id else None
        km = estimate_straight_line_km({"latitude": latitude, "longitude": longitude}, target)
        if km is None:
            return None
        stage, eta = _stage(km, accuracy_m, partner.vehicle_type if partner else None)
        if stage is None:
            return None
        if stage == "arrived":
            _claim(delivery.id, "approaching")  # an arrival makes a later "approaching" pointless
        if not _claim(delivery.id, stage):
            return None
        order = db.get(Order, delivery.order_id)
        if order is None:
            return None
        if stage == "arrived":
            title, body = "Your rider has arrived", (
                f"Your rider is at the drop-off for order {order.order_number}. "
                "Check the package, then give them your handover code.")
        else:
            title, body = f"Your rider is about {eta} min away", (
                f"Order {order.order_number} is nearly there. Have your handover code ready.")
        db.add(Notification(recipient_user_id=order.buyer_user_id, channel="in_app",
                            event_type=f"delivery.rider_{stage}", title=title, body=body))
        record_event(db, delivery=delivery, event_type=f"rider_{stage}",
                     **({"eta_minutes": eta} if stage == "approaching" else {}))
        db.commit()
        return stage
    except RedisError:
        logger.warning("proximity_alert_skipped", extra={"delivery_id": str(delivery.id), "reason": "redis"})
        return None
    except Exception:  # alerts are best-effort; the GPS update itself already succeeded
        db.rollback()
        logger.exception("proximity_alert_failed", extra={"delivery_id": str(delivery.id)})
        return None
