import uuid
from typing import Optional
from pydantic import BaseModel, Field


class GPSPingRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False, strict=True)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False, strict=True)
    eta_minutes: Optional[int] = Field(None, ge=0, le=1440, strict=True)


class TrackingResponse(BaseModel):
    delivery_id: uuid.UUID
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    current_status: str
    eta_minutes: Optional[int] = None

    model_config = {"from_attributes": True}
