import uuid
from pydantic import BaseModel, Field


class CheckoutRequest(BaseModel):
    model_config = {"extra": "forbid"}
    cart_id: uuid.UUID
    cart_revision: int = Field(ge=0)
    vendor_id: uuid.UUID
    delivery_address_id: uuid.UUID
    idempotency_key: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
