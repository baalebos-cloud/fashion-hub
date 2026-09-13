"""Conversation + message CRUD between a customer and a professional."""
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError


class MessagingService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_conversation(self, *, order_id, participant_one_id, participant_two_id):
        from app.models.conversation import Conversation

        conversation = (
            self.db.query(Conversation)
            .filter(
                Conversation.order_id == order_id,
                Conversation.participant_one_id.in_([participant_one_id, participant_two_id]),
                Conversation.participant_two_id.in_([participant_one_id, participant_two_id]),
            )
            .first()
        )
        if conversation:
            return conversation

        conversation = Conversation(
            order_id=order_id, participant_one_id=participant_one_id, participant_two_id=participant_two_id
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def send_message(self, *, conversation_id, sender_user_id, body: str):
        from app.models.conversation import Conversation
        from app.models.message import Message

        conversation = self.db.get(Conversation, conversation_id)
        if not conversation:
            raise NotFoundError("Conversation not found.")
        if str(sender_user_id) not in {str(conversation.participant_one_id), str(conversation.participant_two_id)}:
            raise ForbiddenError("You are not a participant in this conversation.")

        message = Message(conversation_id=conversation_id, sender_user_id=sender_user_id, body=body)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
