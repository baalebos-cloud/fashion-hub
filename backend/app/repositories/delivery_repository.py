from sqlalchemy.orm import Session
from app.models.delivery import Delivery


class DeliveryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_order_id(self, order_id):
        return self.db.query(Delivery).filter(Delivery.order_id == order_id).first()

    def get_by_id(self, delivery_id):
        return self.db.get(Delivery, delivery_id)
