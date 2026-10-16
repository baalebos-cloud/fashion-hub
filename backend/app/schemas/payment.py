import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class InitializePaymentRequest(BaseModel):
    order_id: uuid.UUID
    callback_url: str


class InitializePaymentResponse(BaseModel):
    authorization_url: str
    provider_reference: str


class PaymentResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    provider: str
    provider_reference: str
    amount: float
    currency: str
    status: str
    paid_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
