import uuid
from pydantic import BaseModel, ConfigDict, Field


class CreateAddressRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    label: str = Field(default='Home', min_length=1, max_length=64)
    recipient_name: str = Field(min_length=1, max_length=255)
    recipient_phone: str = Field(min_length=7, max_length=32, pattern=r'^\+?[0-9 ()-]+$')
    formatted_address: str = Field(min_length=5, max_length=512)
    city: str = Field(min_length=1, max_length=128)
    state_region: str = Field(min_length=1, max_length=128)
    country: str = Field(default='NG', pattern=r'^[A-Z]{2}$')
    postal_code: str | None = Field(default=None, max_length=32)


class AddressResponse(CreateAddressRequest):
    id: uuid.UUID
