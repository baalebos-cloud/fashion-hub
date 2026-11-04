"""Privacy-scoped rider GPS, requiring explicit sharing consent.

A random in-memory browser token authorizes the rider's temporary telemetry.
Redis scripts atomically check the consent token and publish the point. A
stop request atomically revokes consent and erases the point, including when
a GPS request is concurrently in flight. Nothing is saved to the rider's
long-term profile or user address.
"""
import hmac
import json
import secrets
from datetime import datetime, timezone

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.exceptions import ExternalProviderError, ForbiddenError

POSITION_TTL_SECONDS = 90
SESSION_TTL_SECONDS = 3600

_PUBLISH_IF_CONSENTED = """
local token = redis.call('GET', KEYS[1])
if token == ARGV[1] then
  redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3])
  return 1
end
return 0
"""


def _client():
    return Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)


def _key(delivery_id, suffix):
    return "delivery:gps:" + str(delivery_id) + ":" + suffix


def start_sharing(delivery_id):
    share_token = secrets.token_urlsafe(32)
    try:
        _client().set(_key(delivery_id, "consent"), share_token, ex=SESSION_TTL_SECONDS)
    except RedisError as exc:
        raise ExternalProviderError("GPS sharing is temporarily unavailable.") from exc
    return {"share_token": share_token}


def save_position(delivery_id, *, share_token, latitude: float, longitude: float, accuracy_m: float):
    point = {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy_m": accuracy_m,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        ok = _client().eval(
            _PUBLISH_IF_CONSENTED, 2,
            _key(delivery_id, "consent"), _key(delivery_id, "point"),
            share_token, json.dumps(point), POSITION_TTL_SECONDS,
        )
    except RedisError as exc:
        raise ExternalProviderError("Rider GPS updates are temporarily unavailable.") from exc
    if ok != 1:
        raise ForbiddenError("GPS sharing is not active. Start sharing again.")
    return point


def read_position(delivery_id):
    try:
        raw = _client().get(_key(delivery_id, "point"))
    except RedisError:
        return None
    if not raw:
        return None
    try:
        payload = json.loads(raw)
        if not all(k in payload for k in ("latitude", "longitude", "accuracy_m", "recorded_at")):
            return None
        return payload
    except (ValueError, TypeError):
        return None


def clear_position(delivery_id):
    try:
        client = _client()
        with client.pipeline(transaction=True) as pipe:
            pipe.delete(_key(delivery_id, "consent"), _key(delivery_id, "point"))
            pipe.execute()
    except RedisError as exc:
        raise ExternalProviderError("Unable to end rider GPS sharing.") from exc
