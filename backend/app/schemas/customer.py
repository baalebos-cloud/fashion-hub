import uuid
from pydantic import BaseModel


class CustomerResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    preferred_currency: str
    default_measurement_profile_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}
