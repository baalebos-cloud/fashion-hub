"""Ephemeral rider-position input and customer-safe output."""
from datetime import datetime

from pydantic import BaseModel, Field


class RiderPositionInput(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    accuracy_m: float = Field(ge=0, le=200, allow_inf_nan=False)
    share_token: str = Field(min_length=32, max_length=128)


class RiderPositionResponse(BaseModel):
    latitude: float
    longitude: float
    accuracy_m: float
    recorded_at: datetime


class RiderSharingSession(BaseModel):
    share_token: str
