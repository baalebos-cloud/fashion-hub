"""Order-bound messaging: only the buyer or seller can access a conversation."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.order import Order
from app.models.user import User
from app.services.messaging_service import MessagingService

router = APIRouter(prefix="/messages", tags=["Messages"])


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    order_id: UUID | None = None
    status: str


class StartConversation(BaseModel):
    order_id: UUID


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    body: str = Field(min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sender_user_id: UUID
    body: str
    is_read: bool
    created_at: datetime


def _owned_conversation(db: Session, conversation_id: UUID, user: User) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise NotFoundError("Conversation not found.")
    if user.id not in {conversation.participant_one_id, conversation.participant_two_id}:
        raise ForbiddenError("You are not a conversation participant.")
    return conversation


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (db.query(Conversation)
            .filter(or_(Conversation.participant_one_id == user.id, Conversation.participant_two_id == user.id))
            .order_by(Conversation.created_at.desc(), Conversation.id).limit(100).all())


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
def start_conversation(payload: StartConversation, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == payload.order_id).with_for_update().first()
    if not order:
        raise NotFoundError("Order not found.")
    if user.id not in {order.buyer_user_id, order.seller_user_id}:
        raise ForbiddenError("Only this order's buyer and seller may start a conversation.")
    return MessagingService(db).get_or_create_conversation(
        order_id=order.id, participant_one_id=order.buyer_user_id,
        participant_two_id=order.seller_user_id,
    )


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def list_messages(conversation_id: UUID, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    _owned_conversation(db, conversation_id, user)
    return (db.query(Message).filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at, Message.id).limit(100).all())


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
def send_message(conversation_id: UUID, payload: MessageCreate,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = _owned_conversation(db, conversation_id, user)
    if conversation.status != "active":
        raise ForbiddenError("This conversation is closed.")
    return MessagingService(db).send_message(
        conversation_id=conversation_id, sender_user_id=user.id, body=payload.body,
    )
