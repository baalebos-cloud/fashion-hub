import uuid
from typing import Optional
from pydantic import BaseModel


class ReviewVerificationRequest(BaseModel):
    approve: bool
    rejection_reason: Optional[str] = None


class AuditLogEntryResponse(BaseModel):
    id: uuid.UUID
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}
