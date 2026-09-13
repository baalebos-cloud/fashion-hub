from sqlalchemy.orm import Session
from app.models.ai_conversation import AIConversation
from app.models.ai_message import AIMessage


class AIRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_conversations_for_user(self, user_id):
        return self.db.query(AIConversation).filter(AIConversation.user_id == user_id).order_by(AIConversation.created_at.desc()).all()

    def list_messages(self, conversation_id):
        return self.db.query(AIMessage).filter(AIMessage.conversation_id == conversation_id).order_by(AIMessage.created_at.asc()).all()
