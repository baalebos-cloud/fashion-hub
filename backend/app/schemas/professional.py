import uuid
from typing import Optional
from pydantic import BaseModel


class ProfessionalResponse(BaseModel):
    id: uuid.UUID
    professional_type: str
    business_name: Optional[str] = None
    bio: Optional[str] = None
    is_verified: bool
    average_rating: float
    review_count: int
    accepts_new_orders: bool

    model_config = {"from_attributes": True}
