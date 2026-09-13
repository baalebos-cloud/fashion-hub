"""
AI assistant conversation orchestration: persists turns, enforces that the
assistant only ever sees context belonging to the current user, and
delegates the actual model call to integrations/ai/navigation_agent.py or
fashion_assistant.py depending on intent.
"""
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError


class AIService:
    def __init__(self, db: Session):
        self.db = db

    def start_conversation(self, *, user_id, title: str | None = None):
        from app.models.ai_conversation import AIConversation

        conversation = AIConversation(user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def send_message(self, *, conversation_id, user_id, content: str) -> dict:
        from app.models.ai_conversation import AIConversation
        from app.models.ai_message import AIMessage

        conversation = self.db.get(AIConversation, conversation_id)
        if not conversation:
            raise NotFoundError("Conversation not found.")
        if str(conversation.user_id) != str(user_id):
            raise ForbiddenError("You do not have access to this conversation.")

        self.db.add(AIMessage(conversation_id=conversation.id, role="user", content=content))
        self.db.commit()

        from app.repositories.user_repository import UserRepository
        from app.integrations.ai.navigation_agent import build_navigation_response

        user = UserRepository(self.db).get_by_id(user_id)
        answer = build_navigation_response(user_role=user.role, user_question=content)

        assistant_message = AIMessage(conversation_id=conversation.id, role="assistant", content=answer)
        self.db.add(assistant_message)
        self.db.commit()
        self.db.refresh(assistant_message)

        return {"conversation_id": str(conversation.id), "answer": answer}
