import uuid
from typing import Optional
from pydantic import BaseModel


class InvoiceLineResponse(BaseModel):
    name: str
    unit_price: float
    quantity: int
    line_total: float


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    invoice_number: str
    order_id: uuid.UUID
    line_items_snapshot: list[InvoiceLineResponse]
    subtotal: float
    delivery_fee: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    currency: str
    payment_status: str
    pdf_url: Optional[str] = None

    model_config = {"from_attributes": True}
