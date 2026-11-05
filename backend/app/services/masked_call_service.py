"""Masked calls between the parties on one order.

Who may call whom (only while the order is open):
- buyer <-> seller (customer <-> tailor/designer, or tailor/designer <-> vendor)
- buyer <-> assigned rider, seller <-> assigned rider (while the delivery is active)

Real numbers are looked up at dial time and never returned by the API or
stored on the call record. When a rider calls the buyer, the delivery
recipient's number from the checkout snapshot is used if present.
"""
from __future__ import annotations

import re
from datetime import timedelta
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.core.timezone import utcnow
from app.integrations.voice import africastalking as voice
from app.models.call_session import CallSession
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.order import Order
from app.models.professional import Professional
from app.models.user import User
from app.models.vendor import Vendor

logger = get_logger(__name__)

Party = Literal["buyer", "seller", "rider"]
CLOSED_ORDER_STATUSES = {"cancelled", "refunded", "rejected", "completed"}
ACTIVE_DELIVERY_STATUSES = {"assigned", "picked_up", "in_transit", "out_for_delivery"}
ALLOWED_PAIRS = {("buyer", "seller"), ("seller", "buyer"), ("buyer", "rider"),
                 ("rider", "buyer"), ("seller", "rider"), ("rider", "seller")}


def normalize_phone(raw: str | None) -> str | None:
    """Best-effort E.164; Nigerian local numbers (0803...) become +234803..."""
    if not raw:
        return None
    digits = re.sub(r"[^\d+]", "", raw)
    if digits.startswith("+"):
        digits = digits[1:]
    elif digits.startswith("00"):
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = "234" + digits[1:]
    return f"+{digits}" if re.fullmatch(r"\d{10,15}", digits) else None


def masked_tail(phone: str | None) -> str | None:
    return phone[-2:] if phone else None


class MaskedCallService:
    def __init__(self, db: Session, place_call=None):
        self.db = db
        self._place_call = place_call or voice.place_call

    # ---- parties -------------------------------------------------------
    def _active_rider(self, order: Order) -> tuple[User | None, Delivery | None]:
        delivery = (self.db.query(Delivery).filter(Delivery.order_id == order.id)
                    .order_by(Delivery.created_at.desc()).first())
        if not delivery or not delivery.delivery_partner_id or delivery.status not in ACTIVE_DELIVERY_STATUSES:
            return None, delivery
        partner = self.db.get(DeliveryPartner, delivery.delivery_partner_id)
        return (self.db.get(User, partner.user_id) if partner else None), delivery

    def _parties(self, order: Order) -> dict[str, User | None]:
        rider, _ = self._active_rider(order)
        return {"buyer": self.db.get(User, order.buyer_user_id),
                "seller": self.db.get(User, order.seller_user_id),
                "rider": rider}

    def _role_of(self, actor: User, parties: dict[str, User | None]) -> str | None:
        for party, user in parties.items():
            if user is not None and str(user.id) == str(actor.id):
                return party
        return None

    def _display_name(self, party: str, user: User) -> str:
        if party == "seller":
            pro = self.db.query(Professional).filter(Professional.user_id == user.id).first()
            if pro and pro.business_name:
                return pro.business_name
            vendor = self.db.query(Vendor).filter(Vendor.user_id == user.id).first()
            if vendor and vendor.business_name:
                return vendor.business_name
        first = (user.full_name or "").strip().split(" ")[0]
        return first or {"buyer": "Customer", "seller": "Seller", "rider": "Rider"}[party]

    def _phone_for(self, party: str, user: User, order: Order, caller_party: str) -> str | None:
        if party == "buyer" and caller_party == "rider":
            snapshot = order.delivery_address_snapshot or {}
            recipient = normalize_phone(snapshot.get("recipient_phone"))
            if recipient:
                return recipient
        return normalize_phone(user.phone_number)

    def _load_order_for(self, actor: User, order_id) -> tuple[Order, dict[str, User | None], str]:
        order = self.db.get(Order, order_id)
        if order is None:
            raise NotFoundError("Order not found.")
        parties = self._parties(order)
        role = self._role_of(actor, parties)
        if role is None:
            raise NotFoundError("Order not found.")
        return order, parties, role

    # ---- public API ----------------------------------------------------
    def contacts(self, *, actor: User, order_id) -> list[dict]:
        """Who the actor can call on this order. Never includes phone numbers."""
        order, parties, role = self._load_order_for(actor, order_id)
        open_order = order.status not in CLOSED_ORDER_STATUSES
        result = []
        for party, user in parties.items():
            if user is None or (role, party) not in ALLOWED_PAIRS:
                continue
            reachable = self._phone_for(party, user, order, role) is not None
            result.append({
                "party": party, "display_name": self._display_name(party, user),
                "available": open_order and reachable,
                "reason": None if open_order and reachable else (
                    "Calls close when an order is finished." if not open_order
                    else "This person hasn't added a phone number yet."),
            })
        return result

    def start_call(self, *, actor: User, order_id, callee: str) -> dict:
        order, parties, role = self._load_order_for(actor, order_id)
        if (role, callee) not in ALLOWED_PAIRS:
            raise ForbiddenError("You can't call that person on this order.")
        if order.status in CLOSED_ORDER_STATUSES:
            raise ConflictError("Calls close when an order is finished.")
        target = parties.get(callee)
        if target is None:
            raise ConflictError("There is no rider on this delivery right now." if callee == "rider"
                                else "That person is not available.")
        caller_phone = normalize_phone(actor.phone_number)
        if caller_phone is None:
            raise ValidationAppError("Add your phone number in Settings so Tailora can connect your call.")
        if self._phone_for(callee, target, order, role) is None:
            raise ConflictError("This person hasn't added a phone number yet. Send them a message instead.")

        session = CallSession(order_id=order.id, caller_user_id=actor.id, callee_user_id=target.id,
                              callee_party=callee, provider=(settings.VOICE_PROVIDER or "none").lower(),
                              status="ringing_caller")
        self.db.add(session)
        self.db.flush()
        try:
            session.provider_session_id = self._place_call(to_phone=caller_phone,
                                                           client_request_id=str(session.id))
        except voice.VoiceNotConfigured:
            self.db.rollback()
            raise
        except Exception:
            session.status = "failed"
            self.db.commit()
            raise
        self.db.commit()
        return {"call_id": str(session.id), "status": session.status,
                "callee_display_name": self._display_name(callee, target),
                "your_phone_ending": masked_tail(caller_phone)}

    # ---- provider webhook ---------------------------------------------
    def handle_voice_event(self, form: dict[str, str]) -> str:
        """Answer an Africa's Talking voice callback with XML."""
        is_active = str(form.get("isActive", "")) == "1"
        session_id = form.get("sessionId") or ""
        direction = (form.get("direction") or "").lower()

        if not is_active:
            self._record_end(session_id, form)
            return ""

        if direction == "inbound":
            return self._route_inbound(normalize_phone(form.get("callerNumber")))

        session = (self.db.query(CallSession).filter(CallSession.provider_session_id == session_id).first()
                   if session_id else None)
        if session is None:
            return voice.xml_response(voice.say("Sorry, this call has expired. Please try again from the Tailora app."))
        order = self.db.get(Order, session.order_id)
        caller = self.db.get(User, session.caller_user_id)
        callee = self.db.get(User, session.callee_user_id)
        if not order or not caller or not callee or order.status in CLOSED_ORDER_STATUSES:
            return voice.xml_response(voice.say("Sorry, this order is no longer open for calls."))
        caller_party = self._role_of(caller, self._parties(order)) or "buyer"
        callee_phone = self._phone_for(session.callee_party, callee, order, caller_party)
        if callee_phone is None:
            return voice.xml_response(voice.say("Sorry, we couldn't reach them. Please send a message in the app."))
        session.status = "connecting"
        self.db.commit()
        return voice.xml_response(voice.say("Connecting your Tailora call. Your number stays private."),
                                  voice.dial(callee_phone))

    def _route_inbound(self, caller_phone: str | None) -> str:
        """Someone rang Tailora's number back: connect them to whoever called them recently."""
        if caller_phone:
            since = utcnow() - timedelta(hours=settings.VOICE_CALLBACK_WINDOW_HOURS)
            recent = (self.db.query(CallSession).filter(CallSession.created_at >= since)
                      .order_by(CallSession.created_at.desc()).limit(50).all())
            for session in recent:
                order = self.db.get(Order, session.order_id)
                callee = self.db.get(User, session.callee_user_id)
                caller = self.db.get(User, session.caller_user_id)
                if not order or not callee or not caller or order.status in CLOSED_ORDER_STATUSES:
                    continue
                parties = self._parties(order)
                caller_party = self._role_of(caller, parties)
                if caller_party is None:
                    continue
                if self._phone_for(session.callee_party, callee, order, caller_party) != caller_phone:
                    continue
                original_caller_phone = normalize_phone(caller.phone_number)
                if original_caller_phone:
                    return voice.xml_response(
                        voice.say("Connecting you back to your Tailora contact."),
                        voice.dial(original_caller_phone))
        return voice.xml_response(voice.say(
            "Thank you for calling Tailora. To reach someone about an order, please use the call button in the Tailora app."))

    def _record_end(self, session_id: str, form: dict[str, str]) -> None:
        if not session_id:
            return
        session = self.db.query(CallSession).filter(CallSession.provider_session_id == session_id).first()
        if session is None:
            return
        try:
            session.duration_seconds = max(0, int(float(form.get("durationInSeconds") or 0)))
        except ValueError:
            session.duration_seconds = None
        session.status = "completed" if (session.duration_seconds or 0) > 0 else "missed"
        self.db.commit()
