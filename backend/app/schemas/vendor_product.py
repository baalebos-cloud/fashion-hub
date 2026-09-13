import uuid
from typing import Optional
from pydantic import BaseModel, Field


class VendorProductCreateRequest(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    base_price: float = Field(..., gt=0)
    category_id: Optional[uuid.UUID] = None


class VendorProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    base_price: float
    currency: str
    is_active: bool

    model_config = {"from_attributes": True}
