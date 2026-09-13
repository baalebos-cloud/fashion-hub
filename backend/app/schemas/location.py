from typing import Optional
from pydantic import BaseModel, Field


class CreateLocationRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    location_type: str
    formatted_address: Optional[str] = None
    city: Optional[str] = None
    state_region: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
