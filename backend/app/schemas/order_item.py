import uuid
from pydantic import BaseModel


class OrderItemResponse(BaseModel):
    id: uuid.UUID
    reference_type: str
    name_snapshot: str
    unit_price: float
    quantity: int
    line_total: float

    model_config = {"from_attributes": True}
