import uuid
from typing import Optional
from pydantic import BaseModel


class MarkDeliveredRequest(BaseModel):
    proof_of_delivery_url: Optional[str] = None


class DeliveryResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    status: str
    delivery_fee: float

    model_config = {"from_attributes": True}
