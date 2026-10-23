import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CreateReviewRequest(BaseModel):
    score: int = Field(..., ge=1, le=5, strict=True)
    comment: Optional[str] = Field(None, max_length=2000)


class ReviewResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    comment: Optional[str] = None
    score: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
