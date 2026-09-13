from sqlalchemy.orm import Session
from app.models.delivery_tracking import DeliveryTracking


class TrackingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_delivery(self, delivery_id):
        return self.db.query(DeliveryTracking).filter(DeliveryTracking.delivery_id == delivery_id).first()
