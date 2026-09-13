"""Delivery tracking read/write. GPS pings are written here; staleness
detection runs as a background job (see workers/tracking_tasks.py)."""
from sqlalchemy.orm import Session

from app.core.timezone import utcnow


class TrackingService:
    def __init__(self, db: Session):
        self.db = db

    def record_gps_ping(self, delivery_id, *, latitude: float, longitude: float, eta_minutes: int | None = None):
        from app.models.delivery_tracking import DeliveryTracking
        from app.models.tracking_event import TrackingEvent

        tracking = self.db.query(DeliveryTracking).filter(DeliveryTracking.delivery_id == delivery_id).first()
        if not tracking:
            tracking = DeliveryTracking(delivery_id=delivery_id, current_status="in_transit")
            self.db.add(tracking)

        tracking.current_latitude = latitude
        tracking.current_longitude = longitude
        tracking.eta_minutes = eta_minutes
        tracking.last_ping_at = utcnow()

        self.db.add(
            TrackingEvent(delivery_id=delivery_id, event_type="gps_ping", latitude=latitude, longitude=longitude)
        )
        self.db.commit()
        return tracking

    def get_tracking_for_order(self, order_id):
        from app.models.delivery import Delivery
        from app.models.delivery_tracking import DeliveryTracking

        delivery = self.db.query(Delivery).filter(Delivery.order_id == order_id).first()
        if not delivery:
            return None
        return self.db.query(DeliveryTracking).filter(DeliveryTracking.delivery_id == delivery.id).first()
