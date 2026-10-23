"""Thin service-layer wrapper kept separate from ai_service.py in case
navigation-specific persistence/analytics (e.g. tracking wrong-navigation
incidents via AIAction.was_helpful) diverges from general AI chat later."""
from sqlalchemy.orm import Session


class AINavigationService:
    def __init__(self, db: Session):
        self.db = db

    def record_feedback(self, ai_message_id, *, user_id, was_helpful: bool):
        from app.models.ai_message import AIMessage
        from app.models.ai_conversation import AIConversation
        from app.core.exceptions import NotFoundError
        message = (self.db.query(AIMessage).join(AIConversation, AIConversation.id == AIMessage.conversation_id)
                   .filter(AIMessage.id == ai_message_id, AIConversation.user_id == user_id, AIMessage.role == "assistant").first())
        if not message:
            raise NotFoundError("Assistant message not found.")
        from app.models.ai_action import AIAction

        action = self.db.query(AIAction).filter(AIAction.ai_message_id == ai_message_id).first()
        if action:
            action.was_helpful = was_helpful
            self.db.commit()
        return action
