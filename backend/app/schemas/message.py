import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    id: uuid.UUID
    sender_user_id: uuid.UUID
    body: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
