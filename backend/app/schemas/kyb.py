from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SubmitKYBRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    business_registration_number: str = Field(min_length=4, max_length=20)
    company_type: Literal["RC", "BN", "IT"] = "RC"
    document_storage_keys: list[str] = Field(min_length=1, max_length=5)


class KYBStatusResponse(BaseModel):
    status: str
    company_type: str | None = None
    business_registration_number: str | None = None
    verified_company_name: str | None = None
    name_match: bool | None = None
    rejection_reason: str | None = None

    model_config = {"from_attributes": True}
