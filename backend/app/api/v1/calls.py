"""
/calls

Calls between the parties on an order (customer, tailor/designer, vendor, rider).
In-app calls (/calls/app, voice over the internet via LiveKit) are the live path; masked
phone calls are kept dormant. The API never returns anyone's phone number.
"""
import hmac
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.integrations.voice import livekit
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
    if livekit.configured():
        # In-app calls don't need anyone's phone number; only the order must be open.
        for contact in contacts:
            closed = contact["reason"] == "Calls close when an order is finished."
            contact.update(available=not closed, reason=contact["reason"] if closed else None)
    elif not settings.VOICE_PROVIDER:
        for contact in contacts:
            contact.update(available=False, reason="In-app calling isn't set up yet.")
    return contacts


# ---- In-app calls ---------------------------------------------------------------------
class AppCallView(BaseModel):
    call_id: str
    status: Literal["ringing", "active", "ended", "declined", "cancelled", "missed"]
    order_id: str
    order_number: str | None = None
    other_party_name: str
    you_are: Literal["caller", "callee"]
    started_at: datetime | None = None
    answered_at: datetime | None = None


class AppCallJoin(AppCallView):
    # Short-lived LiveKit pass for this one call's room (microphone only), and where to connect.
    token: str
    url: str


def _app_calls(db: Session):
    from app.services.app_call_service import AppCallService
    return AppCallService(db)


def _push_after(background: BackgroundTasks, service, *, incoming: str | None = None) -> None:
    """Phone alerts go out after the response: ring for a new call, and replace the alert with
    "Missed call" for calls that stopped ringing unanswered during this request."""
    from app.services import call_push
    if incoming:
        background.add_task(call_push.notify_incoming, incoming)
    for call_id in service.ended_unanswered:
        background.add_task(call_push.notify_missed, call_id)


@router.post("/app", response_model=AppCallJoin, status_code=201)
@limiter.limit("10/10minutes")
def start_app_call(request: Request, payload: StartCallRequest, background: BackgroundTasks,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = _app_calls(db)
    try:
        result = service.start(actor=user, order_id=payload.order_id, callee=payload.callee)
    except livekit.AppCallsNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    _push_after(background, service, incoming=result["call_id"])
    return result


@router.get("/app/incoming", response_model=list[AppCallView])
@limiter.limit("60/minute")
def incoming_app_calls(request: Request, background: BackgroundTasks, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    if not livekit.configured():
        return []
    service = _app_calls(db)
    result = service.incoming(actor=user)
    _push_after(background, service)
    return result


@router.get("/app/{call_id}", response_model=AppCallView)
def app_call_status(call_id: uuid.UUID, background: BackgroundTasks, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    service = _app_calls(db)
    result = service.status(actor=user, call_id=call_id)
    _push_after(background, service)
    return result


@router.post("/app/{call_id}/answer", response_model=AppCallJoin)
def answer_app_call(call_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return _app_calls(db).answer(actor=user, call_id=call_id)
    except livekit.AppCallsNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/app/{call_id}/heartbeat", response_model=AppCallView)
def app_call_heartbeat(call_id: uuid.UUID, background: BackgroundTasks, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    service = _app_calls(db)
    result = service.heartbeat(actor=user, call_id=call_id)
    _push_after(background, service)
    return result


@router.post("/app/{call_id}/decline", response_model=AppCallView)
def decline_app_call(call_id: uuid.UUID, background: BackgroundTasks, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    service = _app_calls(db)
    result = service.decline(actor=user, call_id=call_id)
    _push_after(background, service)
    return result


@router.post("/app/{call_id}/cancel", response_model=AppCallView)
def cancel_app_call(call_id: uuid.UUID, background: BackgroundTasks, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    service = _app_calls(db)
    result = service.cancel(actor=user, call_id=call_id)
    _push_after(background, service)
    return result


@router.post("/app/{call_id}/end", response_model=AppCallView)
def end_app_call(call_id: uuid.UUID, background: BackgroundTasks, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    service = _app_calls(db)
    result = service.end(actor=user, call_id=call_id)
    _push_after(background, service)
    return result


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
