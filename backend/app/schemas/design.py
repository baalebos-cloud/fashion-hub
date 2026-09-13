import uuid
from typing import Optional
from pydantic import BaseModel, Field


class CreateDesignRequest(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    base_price: float = Field(..., gt=0)
    category_id: Optional[uuid.UUID] = None


class DesignResponse(BaseModel):
    id: uuid.UUID
    title: str
    base_price: float
    is_published: bool

    model_config = {"from_attributes": True}
