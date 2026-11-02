import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateAddressRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str = Field(default="Home", min_length=1, max_length=64)
    recipient_name: str = Field(min_length=2, max_length=255)
    recipient_phone: str = Field(min_length=7, max_length=32)
    formatted_address: str = Field(min_length=5, max_length=512)
    city: str = Field(min_length=1, max_length=128)
    state_region: str = Field(min_length=1, max_length=128)
    country: str = Field(default="NG", pattern=r"^[A-Z]{2}$")
    postal_code: str | None = Field(default=None, max_length=32)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    @field_validator("recipient_phone")
    @classmethod
    def validate_recipient_phone(cls, value: str) -> str:
        digits = re.sub(r"[ ()-]", "", value)
        if not re.fullmatch(r"(?:\+234[789][01]\d{8}|0[789][01]\d{8})", digits):
            raise ValueError("Enter a valid Nigerian mobile number.")
        return value


class AddressResponse(CreateAddressRequest):
    id: uuid.UUID
    is_default: bool = False
