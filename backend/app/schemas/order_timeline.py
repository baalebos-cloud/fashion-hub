import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class OrderTimelineEntryResponse(BaseModel):
    from_status: Optional[str] = None
    to_status: str
    actor_user_id: Optional[uuid.UUID] = None
    note: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
