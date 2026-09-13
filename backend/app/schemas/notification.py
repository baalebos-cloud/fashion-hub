import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: uuid.UUID
    channel: str
    event_type: str
    title: str
    body: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
