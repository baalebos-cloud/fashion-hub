from sqlalchemy.orm import Session
from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id, *, unread_only: bool = False, offset: int = 0, limit: int = 20):
        query = self.db.query(Notification).filter(Notification.recipient_user_id == user_id)
        if unread_only:
            query = query.filter(Notification.is_read.is_(False))
        return query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
