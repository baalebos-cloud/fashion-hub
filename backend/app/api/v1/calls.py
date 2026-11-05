"""
/calls

Masked phone calls between the parties on an order (customer, tailor/designer,
vendor, rider). The API never returns anyone's phone number.
"""
import hmac
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.integrations.voice.africastalking import VoiceNotConfigured
from app.models.user import User
from app.services.masked_call_service import MaskedCallService

router = APIRouter(prefix="/calls", tags=["Calls"])


class StartCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: uuid.UUID
    callee: Literal["buyer", "seller", "rider"]


class CallContact(BaseModel):
    party: Literal["buyer", "seller", "rider"]
    display_name: str
    available: bool
    reason: str | None = None


class StartCallResponse(BaseModel):
    call_id: str
    status: str
    callee_display_name: str
    your_phone_ending: str | None


@router.get("/orders/{order_id}/contacts", response_model=list[CallContact])
def call_contacts(order_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contacts = MaskedCallService(db).contacts(actor=user, order_id=order_id)
    if not settings.VOICE_PROVIDER:
        for contact in contacts:
            contact.update(available=False, reason="In-app calling isn't set up yet.")
    return contacts


@router.post("", response_model=StartCallResponse, status_code=201)
@limiter.limit("6/10minutes")
def start_call(request: Request, payload: StartCallRequest,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return MaskedCallService(db).start_call(actor=user, order_id=payload.order_id, callee=payload.callee)
    except VoiceNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/voice/{secret}", include_in_schema=False)
async def voice_webhook(secret: str, request: Request, db: Session = Depends(get_db)):
    """Africa's Talking voice callback. The secret path segment authenticates the provider."""
    expected = settings.VOICE_WEBHOOK_SECRET
    if not expected or not hmac.compare_digest(secret.encode(), expected.encode()):
        raise HTTPException(404)
    form = {k: str(v) for k, v in (await request.form()).items()}
    xml = MaskedCallService(db).handle_voice_event(form)
    return Response(content=xml, media_type="application/xml")
