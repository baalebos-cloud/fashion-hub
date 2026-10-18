import uuid
from pydantic import BaseModel, Field


class RestockRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    quantity_to_add: int = Field(..., gt=0, le=1000000000, strict=True)


class InventoryResponse(BaseModel):
    id: uuid.UUID
    product_variant_id: uuid.UUID
    product_name: str
    sku: str
    quantity_available: int
    quantity_reserved: int

    model_config = {"from_attributes": True}
