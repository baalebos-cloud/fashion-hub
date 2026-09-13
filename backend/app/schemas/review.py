import uuid
from typing import Optional
from pydantic import BaseModel, Field


class CreateReviewRequest(BaseModel):
    score: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=2000)


class ReviewResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    comment: Optional[str] = None

    model_config = {"from_attributes": True}
