import uuid
from typing import Optional
from pydantic import BaseModel, Field


class MarkDeliveredRequest(BaseModel):
    proof_of_delivery_url: Optional[str] = None
    handover_code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")


class MarkPickedUpRequest(BaseModel):
    # Required when DELIVERY_PICKUP_CODE_REQUIRED is on; the seller reads it to the rider.
    pickup_code: Optional[str] = Field(None, min_length=6, max_length=6, pattern=r"^[0-9]{6}$")
    package_count: int = Field(1, ge=1, le=50)


class DeliveryResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    status: str
    delivery_fee: float
    package_count: Optional[int] = None

    model_config = {"from_attributes": True}


class DeliveryTrackingResponse(DeliveryResponse):
    rider_name: Optional[str] = None
    # No rider_phone: customers reach riders through masked calls (POST /calls).
    # Public rider card so customers can check who is coming before handover.
    rider_verified: Optional[bool] = None
    rider_rating: Optional[float] = None
    rider_vehicle_type: Optional[str] = None
    rider_completed_deliveries: Optional[int] = None
    rider_photo_url: Optional[str] = None
