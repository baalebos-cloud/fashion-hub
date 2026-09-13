import uuid
from typing import Optional
from pydantic import BaseModel


class AddressResponse(BaseModel):
    id: uuid.UUID
    label: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    is_default: bool

    model_config = {"from_attributes": True}
