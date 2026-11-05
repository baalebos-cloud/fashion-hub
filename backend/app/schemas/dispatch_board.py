"""Admin-only dispatch metrics; no sensitive customer identity or GPS in list views."""
import uuid
from datetime import datetime

from pydantic import BaseModel


class DispatchRequestSummary(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    status: str
    created_at: datetime


class DispatchRunSummary(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    status: str
    delivery_partner_id: uuid.UUID | None = None
    vehicle_type: str | None = None
    created_at: datetime


class DispatchBoardResponse(BaseModel):
    unassigned_count: int
    active_count: int
    available_verified_riders: int
    pending: list[DispatchRequestSummary]
    active: list[DispatchRunSummary]
