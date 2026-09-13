import uuid
from pydantic import BaseModel, Field


class RecordConsentRequest(BaseModel):
    order_id: uuid.UUID
    amount: float = Field(..., gt=0)
    consent_type: str
    consent_text_version: str


class PaymentConsentResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    amount: float
    consent_type: str
    accepted_at: str

    model_config = {"from_attributes": True}
