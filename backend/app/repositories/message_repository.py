from sqlalchemy.orm import Session
from app.models.message import Message


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_conversation(self, conversation_id, *, offset: int = 0, limit: int = 50):
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )
