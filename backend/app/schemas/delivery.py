import uuid
from typing import Optional
from pydantic import BaseModel, Field


class MarkDeliveredRequest(BaseModel):
    proof_of_delivery_url: Optional[str] = None
    handover_code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")


class DeliveryResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    status: str
    delivery_fee: float

    model_config = {"from_attributes": True}
