import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProfessionalResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    professional_type: str
    business_name: Optional[str] = None
    bio: Optional[str] = None
    years_experience: Optional[int] = None
    is_verified: bool
    average_rating: float
    review_count: int
    accepts_new_orders: bool

    model_config = {"from_attributes": True}


class ProfessionalPage(BaseModel):
    items: list[ProfessionalResponse]
    page: int
    page_size: int
    total: int


class ProfessionalProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    business_name: str = Field(min_length=2, max_length=255)
    bio: str = Field(default="", max_length=4000)
    years_experience: int = Field(default=0, ge=0, le=80)
    accepts_new_orders: bool = True
