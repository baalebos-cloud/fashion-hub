import uuid
from pydantic import BaseModel, Field


class AddCartItemRequest(BaseModel):
    model_config = {"extra": "forbid"}
    product_variant_id: uuid.UUID
    quantity: int = Field(1, ge=1, le=10000, strict=True)


class UpdateCartItemRequest(BaseModel):
    model_config = {"extra": "forbid"}
    quantity: int = Field(..., ge=1, le=10000, strict=True)


class CartItemResponse(BaseModel):
    id: uuid.UUID
    product_variant_id: uuid.UUID
    vendor_id: uuid.UUID
    quantity: int
    unit_price_snapshot: float
    product_name: str
    sku: str
    vendor_name: str
    currency: str
    is_available: bool

    model_config = {"from_attributes": True}


class CartSummaryResponse(BaseModel):
    cart_id: uuid.UUID
    revision: int
    items: list[CartItemResponse]
    subtotal: float
    currency: str
