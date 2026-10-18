import uuid
from typing import Optional
from pydantic import BaseModel, Field


class VendorCreateRequest(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}
    business_name: str = Field(..., min_length=1, max_length=255)
    business_description: Optional[str] = Field(None, max_length=10000)


class VendorResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    business_description: Optional[str] = None
    business_name: str
    is_verified: bool
    average_rating: float

    model_config = {"from_attributes": True}
