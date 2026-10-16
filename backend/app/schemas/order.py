import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference_type: Literal["design"] = "design"
    reference_id: uuid.UUID
    quantity: int = Field(1, ge=1, le=100, strict=True)


class CreateCustomerOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    professional_user_id: uuid.UUID
    items: list[OrderItemCreateRequest] = Field(min_length=1, max_length=50)
    delivery_address_id: uuid.UUID
    measurement_profile_id: uuid.UUID
    idempotency_key: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$")


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    reference_type: str
    reference_id: Optional[uuid.UUID] = None
    name_snapshot: str
    description_snapshot: Optional[str] = None
    unit_price: float
    quantity: int
    line_total: float


class OrderTransitionRequest(BaseModel):
    note: Optional[str] = Field(None, max_length=1000)


class OrderResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    order_type: str
    status: str
    buyer_user_id: uuid.UUID
    seller_user_id: uuid.UUID
    items: list[OrderItemResponse] = Field(default_factory=list)
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
