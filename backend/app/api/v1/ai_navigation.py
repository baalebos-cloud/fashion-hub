"""
/ai/navigation

Backs the global AI assistant widget that lives in the frontend shell (not
a single page) -- every authenticated screen can open the same assistant
and continue the same conversation. Business logic (role-scoped app map,
conversation persistence, ownership checks) lives in AIService; this
module stays a thin route layer.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.ai import AIMessageResponse, SendAIMessageRequest
from app.schemas.ai_navigation import AINavigationFeedbackRequest
from app.services.ai_navigation_service import AINavigationService
from app.services.ai_service import AIService

router = APIRouter(prefix="/ai/navigation", tags=["AI Navigation"])


@router.get("/conversations")
def list_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Conversation history for the current user, so re-opening the widget
    on a different page/device resumes where they left off."""
    from app.repositories.ai_repository import AIRepository

    conversations = AIRepository(db).list_conversations_for_user(current_user.id)
    return [{"id": str(c.id), "title": c.title, "created_at": c.created_at} for c in conversations]


@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.core.exceptions import ForbiddenError, NotFoundError
    from app.models.ai_conversation import AIConversation
    from app.repositories.ai_repository import AIRepository

    conversation = db.get(AIConversation, conversation_id)
    if not conversation:
        raise NotFoundError("Conversation not found.")
    if str(conversation.user_id) != str(current_user.id):
        raise ForbiddenError("You do not have access to this conversation.")

    messages = AIRepository(db).list_messages(conversation_id)
    return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]


@router.post("/messages", response_model=AIMessageResponse)
def send_message(
    payload: SendAIMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Single endpoint the widget calls for every turn. If `conversation_id`
    is omitted, a new conversation is started -- this is what lets the
    frontend open the assistant fresh from any screen with zero setup.
    """
    service = AIService(db)
    conversation_id = payload.conversation_id
    if not conversation_id:
        conversation = service.start_conversation(user_id=current_user.id)
        conversation_id = conversation.id

    result = service.send_message(conversation_id=conversation_id, user_id=current_user.id, content=payload.content)
    return AIMessageResponse(conversation_id=result["conversation_id"], answer=result["answer"])


@router.post("/feedback", status_code=204)
def send_feedback(
    payload: AINavigationFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Thumbs up/down on a specific assistant reply -- feeds back into
    auditing/improving ROLE_APP_MAP and prompts (see docs/ai-assistant.md)."""
    AINavigationService(db).record_feedback(payload.ai_message_id, was_helpful=payload.was_helpful)
    return None
