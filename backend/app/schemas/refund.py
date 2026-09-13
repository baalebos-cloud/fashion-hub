import uuid
from typing import Optional
from pydantic import BaseModel, Field


class RequestRefundRequest(BaseModel):
    order_id: uuid.UUID
    amount: float = Field(..., gt=0)
    reason: Optional[str] = None


class RefundResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    amount: float
    status: str
    reason: Optional[str] = None

    model_config = {"from_attributes": True}
