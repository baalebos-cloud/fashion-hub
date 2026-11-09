"""Ring the person being called on their phones when the Tailora app may be closed.

Runs after the request (FastAPI background task) with its own database session, so a slow or
failing push service never delays or breaks the call itself. A missed or cancelled call
replaces the ringing alert (same collapse id) with "Missed call from …". Dead phone tokens are
removed. No token, phone number or message text is logged.
"""
from __future__ import annotations

import logging
import uuid

from app.core.database import SessionLocal
from app.integrations.notifications import mobile_push
from app.integrations.notifications.mobile_push import PushMessage
from app.models.call_session import CallSession
from app.models.device_token import DeviceToken

logger = logging.getLogger(__name__)


def _deliver(db, user_id, message: PushMessage) -> int:
    sent = 0
    for device in db.query(DeviceToken).filter(DeviceToken.user_id == user_id).all():
        result = mobile_push.send(device.platform, device.token, message)
        if result == "sent":
            sent += 1
        elif result == "invalid":
            db.delete(device)
    db.commit()
    return sent


def _describe(db, call: CallSession):
    from app.services.app_call_service import AppCallService
    from app.models.user import User
    callee = db.get(User, call.callee_user_id)
    return AppCallService(db).describe(call, callee) if callee else None


def notify_incoming(call_id: str) -> None:
    """Called right after a call starts: an urgent, ringing alert to the callee's phones."""
    if not (mobile_push.apns_configured() or mobile_push.fcm_configured()):
        return
    with SessionLocal() as db:
        call = db.get(CallSession, uuid.UUID(str(call_id)))
        if call is None or call.status != "ringing":
            return
        view = _describe(db, call)
        if view is None:
            return
        order = f" about order {view['order_number']}" if view.get("order_number") else ""
        sent = _deliver(db, call.callee_user_id, PushMessage(
            title=f"{view['other_party_name']} is calling",
            body=f"Tailora call{order}. Tap to answer.",
            data={"type": "incoming_call", "call_id": str(call.id), "order_id": str(call.order_id)},
            collapse_id=f"call-{call.id}", ttl_seconds=45, urgent=True))
        logger.info("call_push kind=incoming delivered=%d", sent)


def notify_missed(call_id: str) -> None:
    """Called when a ringing call ends unanswered: replaces the ringing alert."""
    if not (mobile_push.apns_configured() or mobile_push.fcm_configured()):
        return
    with SessionLocal() as db:
        call = db.get(CallSession, uuid.UUID(str(call_id)))
        if call is None or call.status not in ("missed", "cancelled"):
            return
        view = _describe(db, call)
        if view is None:
            return
        _deliver(db, call.callee_user_id, PushMessage(
            title=f"Missed call from {view['other_party_name']}",
            body="Open the order in Tailora to call back.",
            data={"type": "missed_call", "call_id": str(call.id), "order_id": str(call.order_id)},
            collapse_id=f"call-{call.id}", ttl_seconds=24 * 3600, urgent=False))
