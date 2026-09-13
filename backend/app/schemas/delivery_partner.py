import uuid
from pydantic import BaseModel


class SetAvailabilityRequest(BaseModel):
    is_available: bool


class DeliveryPartnerResponse(BaseModel):
    id: uuid.UUID
    vehicle_type: str | None = None
    is_verified: bool
    is_available: bool
    average_rating: float

    model_config = {"from_attributes": True}
