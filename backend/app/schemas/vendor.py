import uuid
from typing import Optional
from pydantic import BaseModel, Field


class VendorCreateRequest(BaseModel):
    business_name: str = Field(..., max_length=255)
    business_description: Optional[str] = None


class VendorResponse(BaseModel):
    id: uuid.UUID
    business_name: str
    is_verified: bool
    average_rating: float

    model_config = {"from_attributes": True}
