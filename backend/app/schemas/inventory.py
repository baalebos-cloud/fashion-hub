import uuid
from pydantic import BaseModel, Field


class RestockRequest(BaseModel):
    quantity_to_add: int = Field(..., gt=0)


class InventoryResponse(BaseModel):
    id: uuid.UUID
    product_variant_id: uuid.UUID
    quantity_available: int
    quantity_reserved: int

    model_config = {"from_attributes": True}
