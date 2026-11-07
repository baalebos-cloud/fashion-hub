"""Ephemeral rider-position input and customer-safe output."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RiderPositionInput(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    accuracy_m: float = Field(ge=0, le=200, allow_inf_nan=False)
    share_token: str = Field(min_length=32, max_length=128)
    # When the phone took the fix (GeolocationPosition.timestamp). Used to reject stale,
    # replayed and out-of-order points. Optional for older app versions.
    recorded_at: datetime | None = None
    speed_mps: float | None = Field(None, ge=0, le=70, allow_inf_nan=False)


class RiderPositionResponse(BaseModel):
    latitude: float
    longitude: float
    accuracy_m: float
    recorded_at: datetime
    # live | delayed | last_known. A last_known point is "last seen", never the current position.
    freshness: str | None = None
    age_seconds: int | None = None
    accepted: bool | None = None      # on publish: False when ignored as too frequent
    sharing: bool | None = None
    device_state: str | None = None


class RiderDeviceStateInput(BaseModel):
    share_token: str = Field(min_length=32, max_length=128)
    state: Literal["permission_denied", "unavailable", "paused"]


class RiderSharingSession(BaseModel):
    share_token: str
