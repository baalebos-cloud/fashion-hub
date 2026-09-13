import uuid
from typing import Optional
from pydantic import BaseModel


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    invoice_number: str
    order_id: uuid.UUID
    subtotal: float
    delivery_fee: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    currency: str
    payment_status: str
    pdf_url: Optional[str] = None

    model_config = {"from_attributes": True}
