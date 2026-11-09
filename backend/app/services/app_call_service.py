"""In-app calls between the parties on one order (voice over the internet, no phone numbers).

Same rules as masked calls (masked_call_service.ALLOWED_PAIRS): customer <-> seller, and either
of them <-> the assigned rider while the delivery is active, only while the order is open.

Lifecycle of a call (CallSession, provider "livekit"):
  ringing --answer--> active --end--> ended
  ringing --decline--> declined | --cancel (caller)--> cancelled | --no answer--> missed
Nothing is recorded; LiveKit only relays the audio. A missed call leaves a notification.
"""
from __future__ import annotations

import secrets
from datetime import timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.timezone import utcnow
from app.integrations.voice import livekit
from app.models.call_session import CallSession
from app.models.notification import Notification
from app.models.order import Order
from app.models.user import User
from app.services.masked_call_service import ALLOWED_PAIRS, CLOSED_ORDER_STATUSES, MaskedCallService

PROVIDER = "livekit"
OPEN = ("ringing", "active")


def _aware(value):
    return value if value is None or value.tzinfo else value.replace(tzinfo=timezone.utc)


class AppCallService:
    def __init__(self, db: Session):
        self.db = db
        self.parties = MaskedCallService(db)  # reuse who-may-call-whom and display names
        # Calls that stopped ringing without an answer during this request (missed or
        # cancelled): the API replaces their phone alert afterwards (services/call_push.py).
        self.ended_unanswered: list[str] = []

    # ---- helpers ---------------------------------------------------------
    def _ring_window(self) -> timedelta:
        return timedelta(seconds=settings.APP_CALL_RING_SECONDS)

    def _expire_if_unanswered(self, call: CallSession) -> None:
        """Settle calls nobody is looking after any more:
        - ringing past the ring window -> missed (once, with a notification);
        - answered but silent (no heartbeat) past APP_CALL_STALE_SECONDS, or past the maximum
          call length -> ended, so closing the app mid-call can't leave anyone stuck "on a call"."""
        now = utcnow()
        if call.status == "active":
            last = _aware(call.last_seen_at) or _aware(call.answered_at) or _aware(call.created_at)
            answered = _aware(call.answered_at) or last
            stale = now - last > timedelta(seconds=settings.APP_CALL_STALE_SECONDS)
            too_long = now - answered > timedelta(seconds=settings.VOICE_MAX_CALL_SECONDS)
            if stale or too_long:
                call.status = "ended"
                call.ended_at = min(now, last + timedelta(seconds=settings.APP_CALL_STALE_SECONDS)) if stale else now
                call.duration_seconds = max(0, int((call.ended_at - answered).total_seconds()))
            return
        if call.status == "ringing" and now - _aware(call.created_at) > self._ring_window():
            call.status = "missed"
            call.ended_at = utcnow()
            self.ended_unanswered.append(str(call.id))
            caller = self.db.get(User, call.caller_user_id)
            order = self.db.get(Order, call.order_id)
            self.db.add(Notification(
                recipient_user_id=call.callee_user_id, channel="in_app", event_type="call.missed",
                title="Missed call",
                body=f"{self._caller_name(call, caller)} tried to call you about order "
                     f"{order.order_number if order else ''}. Open the order to call back."))

    def _caller_name(self, call: CallSession, caller: User | None) -> str:
        if caller is None:
            return "Someone"
        order = self.db.get(Order, call.order_id)
        party = self.parties._role_of(caller, self.parties._parties(order)) if order else None
        return self.parties._display_name(party or "buyer", caller)

    def _get(self, call_id, actor: User, *, lock: bool = False) -> CallSession:
        query = self.db.query(CallSession).filter(CallSession.id == call_id, CallSession.provider == PROVIDER)
        call = (query.with_for_update() if lock else query).first()
        if call is None or str(actor.id) not in {str(call.caller_user_id), str(call.callee_user_id)}:
            raise NotFoundError("Call not found.")
        return call

    def _busy(self, user_id) -> bool:
        for call in (self.db.query(CallSession)
                     .filter(CallSession.provider == PROVIDER, CallSession.status.in_(OPEN),
                             (CallSession.caller_user_id == user_id) | (CallSession.callee_user_id == user_id)).all()):
            self._expire_if_unanswered(call)
            if call.status in OPEN:
                return True
        return False

    def _lock_people(self, *user_ids) -> None:
        """One call at a time per person: requests involving the same people are handled one after
        the other (locks held until commit, always taken in the same order to avoid deadlocks)."""
        from sqlalchemy import text
        for user_id in sorted({str(u) for u in user_ids}):
            self.db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": "app-call-user:" + user_id})

    def _token(self, call: CallSession, user: User, name: str) -> str:
        ttl = timedelta(seconds=settings.VOICE_MAX_CALL_SECONDS) + self._ring_window() + timedelta(minutes=1)
        return livekit.join_token(room=call.room_name, identity=str(user.id), name=name, ttl=ttl)

    def describe(self, call: CallSession, viewer: User) -> dict:
        other_id = call.callee_user_id if str(viewer.id) == str(call.caller_user_id) else call.caller_user_id
        other = self.db.get(User, other_id)
        order = self.db.get(Order, call.order_id)
        party = self.parties._role_of(other, self.parties._parties(order)) if (other and order) else None
        return {"call_id": str(call.id), "status": call.status, "order_id": str(call.order_id),
                "order_number": order.order_number if order else None,
                "other_party_name": self.parties._display_name(party or "buyer", other) if other else "Someone",
                "you_are": "caller" if str(viewer.id) == str(call.caller_user_id) else "callee",
                "started_at": _aware(call.created_at), "answered_at": _aware(call.answered_at)}

    # ---- actions ---------------------------------------------------------
    def start(self, *, actor: User, order_id, callee: str) -> dict:
        if not livekit.configured():
            raise livekit.AppCallsNotConfigured("In-app calling isn't set up yet.")
        order, parties, role = self.parties._load_order_for(actor, order_id)
        if (role, callee) not in ALLOWED_PAIRS:
            raise ForbiddenError("You can't call that person on this order.")
        if order.status in CLOSED_ORDER_STATUSES:
            raise ConflictError("Calls close when an order is finished.")
        target = parties.get(callee)
        if target is None:
            raise ConflictError("There is no rider on this delivery right now." if callee == "rider"
                                else "That person is not available.")
        self._lock_people(actor.id, target.id)
        if self._busy(actor.id):
            self.db.commit()
            raise ConflictError("You're already on a call.")
        if self._busy(target.id):
            self.db.commit()
            raise ConflictError(f"{self.parties._display_name(callee, target)} is on another call. Try again shortly.")
        call = CallSession(order_id=order.id, caller_user_id=actor.id, callee_user_id=target.id, callee_party=callee,
                           provider=PROVIDER, status="ringing", room_name="call-" + secrets.token_hex(16))
        self.db.add(call)
        self.db.flush()
        result = {**self.describe(call, actor), "token": self._token(call, actor, self.parties._display_name(role, actor)),
                  "url": settings.LIVEKIT_URL}
        self.db.commit()
        return result

    def incoming(self, *, actor: User) -> list[dict]:
        """Calls ringing for this person now (the app checks this every few seconds)."""
        calls = (self.db.query(CallSession)
                 .filter(CallSession.provider == PROVIDER, CallSession.callee_user_id == actor.id,
                         CallSession.status == "ringing").order_by(CallSession.created_at).all())
        for call in calls:
            self._expire_if_unanswered(call)
        self.db.commit()
        return [self.describe(c, actor) for c in calls if c.status == "ringing"]

    def status(self, *, actor: User, call_id) -> dict:
        call = self._get(call_id, actor, lock=True)
        self._expire_if_unanswered(call)
        self.db.commit()
        return self.describe(call, actor)

    def answer(self, *, actor: User, call_id) -> dict:
        call = self._get(call_id, actor, lock=False)
        if str(actor.id) != str(call.callee_user_id):
            raise ForbiddenError("Only the person being called can answer.")
        self._lock_people(call.caller_user_id, call.callee_user_id)
        call = self._get(call_id, actor, lock=True)
        self._expire_if_unanswered(call)
        others = (self.db.query(CallSession)
                  .filter(CallSession.provider == PROVIDER, CallSession.status == "active", CallSession.id != call.id,
                          (CallSession.caller_user_id == actor.id) | (CallSession.callee_user_id == actor.id)).all())
        for other in others:
            self._expire_if_unanswered(other)
        if any(o.status == "active" for o in others):
            self.db.commit()
            raise ConflictError("You're already on another call. Hang up first.")
        if call.status != "ringing":
            self.db.commit()
            raise ConflictError("This call has ended." if call.status != "active" else "This call is already answered.")
        order = self.db.get(Order, call.order_id)
        if order is None or order.status in CLOSED_ORDER_STATUSES:
            raise ConflictError("Calls close when an order is finished.")
        call.status = "active"
        call.answered_at = utcnow()
        call.last_seen_at = call.answered_at
        role = self.parties._role_of(actor, self.parties._parties(order)) or call.callee_party
        result = {**self.describe(call, actor), "token": self._token(call, actor, self.parties._display_name(role, actor)),
                  "url": settings.LIVEKIT_URL}
        self.db.commit()
        return result

    def _finish(self, *, actor: User, call_id, allowed_from: tuple[str, ...], who: str, to: str) -> dict:
        call = self._get(call_id, actor, lock=True)
        if who == "callee" and str(actor.id) != str(call.callee_user_id):
            raise ForbiddenError("Only the person being called can decline.")
        if who == "caller" and str(actor.id) != str(call.caller_user_id):
            raise ForbiddenError("Only the caller can cancel.")
        self._expire_if_unanswered(call)
        if call.status in allowed_from:
            now = utcnow()
            if to == "cancelled":
                self.ended_unanswered.append(str(call.id))
            call.status = to
            call.ended_at = now
            if to == "ended" and call.answered_at:
                call.duration_seconds = max(0, int((now - _aware(call.answered_at)).total_seconds()))
        self.db.commit()
        return self.describe(call, actor)  # repeating a finish is harmless

    def heartbeat(self, *, actor: User, call_id) -> dict:
        """Either person's app says "still here" during an answered call (every ~15 s)."""
        call = self._get(call_id, actor, lock=True)
        self._expire_if_unanswered(call)
        if call.status == "active":
            call.last_seen_at = utcnow()
        self.db.commit()
        return self.describe(call, actor)

    def decline(self, *, actor: User, call_id) -> dict:
        return self._finish(actor=actor, call_id=call_id, allowed_from=("ringing",), who="callee", to="declined")

    def cancel(self, *, actor: User, call_id) -> dict:
        return self._finish(actor=actor, call_id=call_id, allowed_from=("ringing",), who="caller", to="cancelled")

    def end(self, *, actor: User, call_id) -> dict:
        return self._finish(actor=actor, call_id=call_id, allowed_from=("active",), who="either", to="ended")
