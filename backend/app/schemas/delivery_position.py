"""Ephemeral, accuracy-tagged rider position for active deliveries."""
from datetime import datetime

from pydantic import BaseModel, Field


class RiderPositionInput(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    accuracy_m: float = Field(ge=0, le=200, allow_inf_nan=False)


class RiderPositionResponse(RiderPositionInput):
    recorded_at: datetime
