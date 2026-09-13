import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OrderItemCreateRequest(BaseModel):
    reference_type: str  # design | service
    reference_id: Optional[uuid.UUID] = None
    name_snapshot: str
    unit_price: float = Field(..., gt=0)
    quantity: int = Field(1, ge=1)


class CreateCustomerOrderRequest(BaseModel):
    professional_user_id: uuid.UUID
    items: list[OrderItemCreateRequest]
    delivery_address_id: uuid.UUID
    measurement_profile_id: Optional[uuid.UUID] = None
    idempotency_key: Optional[str] = Field(None, max_length=128)


class OrderTransitionRequest(BaseModel):
    note: Optional[str] = Field(None, max_length=1000)


class OrderResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    order_type: str
    status: str
    subtotal: float
    delivery_fee: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    currency: str
    ordered_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    production_started_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    out_for_delivery_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
