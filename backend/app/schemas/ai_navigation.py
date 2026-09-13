import uuid
from pydantic import BaseModel


class AINavigationFeedbackRequest(BaseModel):
    ai_message_id: uuid.UUID
    was_helpful: bool
