"""One-time, expiring delivery codes (pickup and handover) and the delivery event log.

- The handover code is shown only to the buyer, after pickup; the rider types it in at the door.
- The pickup code is shown only to the seller, once a rider is assigned; the rider types it in
  when collecting the package.
- Codes are never stored: each row keeps a random nonce and the six digits are
  HMAC(SECRET_KEY, purpose|delivery|nonce). Codes expire, can be rotated by their holder,
  and are marked used on success so they cannot be replayed.
- Wrong guesses share a Redis attempt limit across API workers; Redis outages fail closed.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import UTC, timedelta

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    ExternalProviderError,
    ForbiddenError,
    ValidationAppError,
)
from app.core.timezone import utcnow
from app.models.delivery import Delivery
from app.models.delivery_proof import DeliveryCode, DeliveryEvent

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 1800
PURPOSES = {"pickup", "handover"}
IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9_:\-]{8,80}$")
PROMPT = {"pickup": "Enter the six-digit pickup code from the seller.",
          "handover": "Enter the six-digit code provided by the customer."}


def _aware(value):
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _ttl(purpose: str) -> timedelta:
    minutes = settings.PICKUP_CODE_TTL_MINUTES if purpose == "pickup" else settings.HANDOVER_CODE_TTL_MINUTES
    return timedelta(minutes=max(1, minutes))


def derive_code(purpose: str, delivery_id, nonce: str) -> str:
    message = f"fashion-hub:delivery-{purpose}:{delivery_id}:{nonce}".encode()
    digest = hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).digest()
    return f"{int.from_bytes(digest[:8], 'big') % 1000000:06d}"


def validate_idempotency_key(key: str | None) -> str | None:
    if key is None or key == "":
        return None
    if not IDEMPOTENCY_KEY.match(key):
        raise ValidationAppError("Idempotency-Key must be 8-80 letters, digits, '-', '_' or ':'.")
    return key


def record_event(db: Session, *, delivery: Delivery, event_type: str, actor=None,
                 idempotency_key: str | None = None, **details) -> DeliveryEvent:
    """Append an event. Callers commit. Details must never include codes or contact data."""
    event = DeliveryEvent(delivery_id=delivery.id, order_id=delivery.order_id, event_type=event_type,
                          actor_user_id=getattr(actor, "id", None), actor_role=getattr(actor, "role", None),
                          idempotency_key=idempotency_key, details=details or None)
    db.add(event)
    return event


class DeliveryCodeService:
    def __init__(self, db: Session):
        self.db = db

    def _live(self, delivery_id, purpose) -> DeliveryCode | None:
        return (self.db.query(DeliveryCode)
                .filter(DeliveryCode.delivery_id == delivery_id, DeliveryCode.purpose == purpose,
                        DeliveryCode.used_at.is_(None), DeliveryCode.revoked_at.is_(None))
                .with_for_update().populate_existing().first())

    def reveal(self, *, delivery: Delivery, purpose: str, actor, rotate: bool = False) -> dict:
        """Return the current code for its holder, issuing a new one if none is live, it has
        expired, or the holder asked for a fresh one. The caller must hold the delivery row lock."""
        assert purpose in PURPOSES
        now = utcnow()
        current = self._live(delivery.id, purpose)
        if current is not None and not rotate and _aware(current.expires_at) > now:
            return {"code": derive_code(purpose, delivery.id, current.nonce), "expires_at": current.expires_at}
        if current is not None:
            current.revoked_at = now
            self.db.flush()  # free the one-live-code slot before inserting the replacement
        fresh = DeliveryCode(delivery_id=delivery.id, purpose=purpose, nonce=secrets.token_urlsafe(24),
                             expires_at=now + _ttl(purpose))
        self.db.add(fresh)
        record_event(self.db, delivery=delivery, event_type=f"{purpose}_code_issued", actor=actor,
                     reason="rotated" if rotate and current is not None else
                     "expired" if current is not None else "first")
        self.db.flush()
        return {"code": derive_code(purpose, delivery.id, fresh.nonce), "expires_at": fresh.expires_at}

    def verify(self, *, delivery: Delivery, purpose: str, submitted: str | None) -> None:
        """Check a code the rider typed in and burn it on success. Raises on any failure."""
        if not submitted or len(submitted) != 6 or not submitted.isascii() or not submitted.isdecimal():
            raise ValidationAppError(PROMPT[purpose])
        key = f"delivery:{purpose}:attempts:{delivery.id}"
        try:
            redis = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
            count = redis.incr(key)
            if count == 1:
                redis.expire(key, WINDOW_SECONDS)
        except RedisError as exc:
            raise ExternalProviderError("Delivery confirmation is unavailable. Try again later.") from exc
        if count > MAX_ATTEMPTS:
            raise ForbiddenError("Too many incorrect codes. Contact support.")
        live = self._live(delivery.id, purpose)
        holder = "seller" if purpose == "pickup" else "customer"
        if live is None or _aware(live.expires_at) <= utcnow():
            # Same response whether there was never a code or it lapsed: the holder refreshes it.
            raise ValidationAppError(f"That code has expired. Ask the {holder} to open their code again.")
        if not hmac.compare_digest(derive_code(purpose, delivery.id, live.nonce), submitted):
            raise ValidationAppError(f"Incorrect {purpose} code.")
        live.used_at = utcnow()
        try:
            redis.delete(key)
        except RedisError:
            pass  # counter expires on its own
