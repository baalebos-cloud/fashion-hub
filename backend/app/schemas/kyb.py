from typing import Optional
from pydantic import BaseModel


class SubmitKYBRequest(BaseModel):
    business_registration_number: str
    document_storage_keys: list[str]


class KYBStatusResponse(BaseModel):
    status: str
    rejection_reason: Optional[str] = None

    model_config = {"from_attributes": True}
