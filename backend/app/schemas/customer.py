import uuid
from pydantic import BaseModel


class CustomerResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    preferred_currency: str

    model_config = {"from_attributes": True}
