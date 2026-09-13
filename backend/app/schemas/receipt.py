import uuid
from typing import Optional
from pydantic import BaseModel


class ReceiptResponse(BaseModel):
    id: uuid.UUID
    receipt_number: str
    amount_paid: float
    currency: str
    pdf_url: Optional[str] = None

    model_config = {"from_attributes": True}
