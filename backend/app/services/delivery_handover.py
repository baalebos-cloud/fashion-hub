"""Customer-only handover codes, with shared Redis attempt limits.

Codes are derived from a server secret, never exposed to the rider API.
Redis outages fail closed to prevent unbounded guessing.
"""
import hashlib
import hmac

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.exceptions import ExternalProviderError, ForbiddenError, ValidationAppError

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 1800


def handover_code(delivery_id) -> str:
    message = ("fashion-hub:delivery-handover:" + str(delivery_id)).encode()
    digest = hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).digest()
    return f"{int.from_bytes(digest[:8], 'big') % 1000000:06d}"


def verify_handover_code(delivery_id, submitted: str | None) -> None:
    if not submitted or len(submitted) != 6 or not submitted.isascii() or not submitted.isdecimal():
        raise ValidationAppError("Enter the six-digit code provided by the customer.")
    key = "delivery:handover:attempts:" + str(delivery_id)
    try:
        redis = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        # Shared limiter across API workers; no local in-memory bypass.
        count = redis.incr(key)
        if count == 1:
            redis.expire(key, WINDOW_SECONDS)
    except RedisError as exc:
        raise ExternalProviderError("Delivery confirmation is unavailable. Try again later.") from exc
    if count > MAX_ATTEMPTS:
        raise ForbiddenError("Too many incorrect delivery codes. Contact support.")
    if not hmac.compare_digest(handover_code(delivery_id), submitted):
        raise ValidationAppError("Incorrect delivery confirmation code.")
    redis.delete(key)
