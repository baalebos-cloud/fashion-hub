import uuid
from typing import Optional
from pydantic import BaseModel


class CreateDeliveryRequestSchema(BaseModel):
    order_id: uuid.UUID
    pickup_location_id: uuid.UUID
    dropoff_location_id: uuid.UUID
    package_description: Optional[str] = None


class RejectDeliveryRequestSchema(BaseModel):
    reason: str


class DeliveryRequestResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    status: str

    model_config = {"from_attributes": True}
