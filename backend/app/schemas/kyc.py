from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class SubmitKYCRequest(BaseModel):
    nin_number: str = Field(..., min_length=11, max_length=11, description="11-digit Nigerian National Identity Number")
    document_storage_keys: list[str] = Field(..., min_length=1, description="Supporting ID document photos, already uploaded")
    home_latitude: float = Field(..., ge=-90, le=90)
    home_longitude: float = Field(..., ge=-180, le=180)
    home_formatted_address: Optional[str] = None


class KYCStatusResponse(BaseModel):
    """Deliberately excludes nin_number and id_number_encrypted -- the raw
    NIN is never returned by any API response, only what was verified
    against it."""
    status: str
    id_type: Optional[str] = None
    nin_verified_full_name: Optional[str] = None
    nin_verified_date_of_birth: Optional[date] = None
    nin_verified_gender: Optional[str] = None
    identity_match: Optional[bool] = None
    rejection_reason: Optional[str] = None

    model_config = {"from_attributes": True}
