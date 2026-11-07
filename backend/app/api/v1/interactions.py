"""Shopping activity for personalised recommendations, and the opt-out switch.

POST /interactions/events takes small batches from the website: views, searches and started
bookings. It works signed in or out (signed-out visitors send a random browser ID), and is not
written to the admin activity log, so no IP address is kept alongside the activity.
"""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user
from app.core.rate_limit import limiter
from app.models.user import User
from app.services import interaction_service

router = APIRouter(prefix="/interactions", tags=["Recommendations"])


class InteractionIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    event_type: Literal["view", "search", "booking_started"]
    item_type: Literal["product", "design", "professional"] | None = None
    item_id: UUID | None = None
    search_query: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default=None, max_length=32)


class InteractionBatch(BaseModel):
    anonymous_id: UUID | None = None
    events: list[InteractionIn] = Field(min_length=1, max_length=interaction_service.MAX_BATCH)


class PersonalizationPreference(BaseModel):
    personalization_enabled: bool


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.RATE_LIMIT_INTERACTIONS)
def record_events(
    request: Request,
    batch: InteractionBatch,
    user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    accepted = interaction_service.record_batch(
        db, user=user, anonymous_id=str(batch.anonymous_id) if batch.anonymous_id else None,
        events=[event.model_dump() for event in batch.events])
    return {"accepted": accepted}


@router.get("/preference", response_model=PersonalizationPreference)
def get_preference(user: User = Depends(get_current_user)):
    return {"personalization_enabled": user.personalization_enabled}


@router.put("/preference", response_model=PersonalizationPreference)
def set_preference(body: PersonalizationPreference, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    enabled = interaction_service.set_personalization(db, user, body.personalization_enabled)
    return {"personalization_enabled": enabled}
