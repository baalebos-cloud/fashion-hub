from typing import Optional

from sqlalchemy.orm import Session

from app.models.order import Order


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, order_id) -> Optional[Order]:
        return self.db.get(Order, order_id)

    def get_by_id_for_update(self, order_id) -> Optional[Order]:
        """SELECT ... FOR UPDATE row lock, used before any status transition
        to prevent two concurrent requests (e.g. a duplicate webhook and a
        manual admin action) from racing on the same order."""
        return self.db.query(Order).filter(Order.id == order_id).with_for_update().first()

    def get_by_order_number(self, order_number: str) -> Optional[Order]:
        return self.db.query(Order).filter(Order.order_number == order_number).first()

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Order]:
        return self.db.query(Order).filter(Order.idempotency_key == idempotency_key).first()

    def list_for_buyer(self, buyer_user_id, *, order_type: Optional[str] = None, offset: int = 0, limit: int = 20):
        query = self.db.query(Order).filter(Order.buyer_user_id == buyer_user_id)
        if order_type:
            query = query.filter(Order.order_type == order_type)
        return query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

    def list_for_seller(self, seller_user_id, *, order_type: Optional[str] = None, offset: int = 0, limit: int = 20):
        query = self.db.query(Order).filter(Order.seller_user_id == seller_user_id)
        if order_type:
            query = query.filter(Order.order_type == order_type)
        return query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

    def add(self, order: Order) -> Order:
        self.db.add(order)
        return order
