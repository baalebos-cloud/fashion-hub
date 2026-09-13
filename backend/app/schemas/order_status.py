from pydantic import BaseModel


class OrderStatusDefinitionResponse(BaseModel):
    order_type: str
    code: str
    label: str
    sort_order: int

    model_config = {"from_attributes": True}
