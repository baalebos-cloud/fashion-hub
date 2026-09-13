import uuid
from pydantic import BaseModel, Field


class AddCartItemRequest(BaseModel):
    product_variant_id: uuid.UUID
    quantity: int = Field(1, ge=1)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., ge=1)


class CartItemResponse(BaseModel):
    id: uuid.UUID
    product_variant_id: uuid.UUID
    vendor_id: uuid.UUID
    quantity: int
    unit_price_snapshot: float

    model_config = {"from_attributes": True}


class CartSummaryResponse(BaseModel):
    cart_id: uuid.UUID
    items: list[CartItemResponse]
    subtotal: float
