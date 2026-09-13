from sqlalchemy.orm import Session
from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_order_id(self, order_id):
        return self.db.query(Payment).filter(Payment.order_id == order_id).first()

    def get_by_reference(self, provider_reference: str):
        return self.db.query(Payment).filter(Payment.provider_reference == provider_reference).first()
