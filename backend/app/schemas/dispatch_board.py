"""Admin-only dispatch metrics; no sensitive customer identity or GPS in list views."""
import uuid
from datetime import datetime

from pydantic import BaseModel


class DispatchRequestSummary(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    order_number: str | None = None
    order_type: str | None = None
    status: str
    created_at: datetime
    offered_to: str | None = None
    offer_expires_at: datetime | None = None
    offer_attempt: int | None = None


class DispatchRunSummary(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    status: str
    order_number: str | None = None
    order_type: str | None = None
    delivery_partner_id: uuid.UUID | None = None
    rider_first_name: str | None = None
    vehicle_type: str | None = None
    open_issue_count: int = 0
    created_at: datetime
    # Location freshness only (live / delayed / last_known / not_sharing / permission_denied); no coordinates.
    tracking: dict | None = None


class DispatchBoardResponse(BaseModel):
    unassigned_count: int
    active_count: int
    available_verified_riders: int
    open_issue_count: int = 0
    auto_offers_enabled: bool = False
    pending: list[DispatchRequestSummary]
    active: list[DispatchRunSummary]


class DispatchActionReason(BaseModel):
    reason: str


class ReassignRequest(DispatchActionReason):
    partner_id: uuid.UUID


class IssueUpdateRequest(BaseModel):
    status: str
    note: str | None = None
