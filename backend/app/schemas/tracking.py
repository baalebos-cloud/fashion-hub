import uuid
from typing import Optional
from pydantic import BaseModel


class GPSPingRequest(BaseModel):
    latitude: float
    longitude: float
    eta_minutes: Optional[int] = None


class TrackingResponse(BaseModel):
    delivery_id: uuid.UUID
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    current_status: str
    eta_minutes: Optional[int] = None

    model_config = {"from_attributes": True}
