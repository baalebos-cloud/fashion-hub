from sqlalchemy.orm import Session
from app.models.order_timeline import OrderTimelineEntry


class OrderTimelineRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_order(self, order_id):
        return (
            self.db.query(OrderTimelineEntry)
            .filter(OrderTimelineEntry.order_id == order_id)
            .order_by(OrderTimelineEntry.created_at.asc())
            .all()
        )
