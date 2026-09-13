from sqlalchemy.orm import Session
from app.models.refund import Refund


class RefundRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, refund_id):
        return self.db.get(Refund, refund_id)

    def list_for_order(self, order_id):
        return self.db.query(Refund).filter(Refund.order_id == order_id).all()
