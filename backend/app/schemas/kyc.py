from typing import Optional
from pydantic import BaseModel


class SubmitKYCRequest(BaseModel):
    id_type: str
    document_storage_keys: list[str]


class KYCStatusResponse(BaseModel):
    status: str
    rejection_reason: Optional[str] = None

    model_config = {"from_attributes": True}
