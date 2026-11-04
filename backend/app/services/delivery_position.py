"""Ephemeral rider GPS, restricted to an active assigned delivery.

Positions expire after 90 seconds and are never stored on user profiles.
No geolocation is inferred from orders or exposed to unassigned couriers.
"""
import json
from datetime import datetime, timezone

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.exceptions import ExternalProviderError

POSITION_TTL_SECONDS = 90


def _client():
    return Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)


def _key(delivery_id):
    return "delivery:live-position:" + str(delivery_id)


def save_position(delivery_id, *, latitude: float, longitude: float, accuracy_m: float):
    point = {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy_m": accuracy_m,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        _client().set(_key(delivery_id), json.dumps(point), ex=POSITION_TTL_SECONDS)
    except RedisError as exc:
        raise ExternalProviderError("Rider GPS updates are temporarily unavailable.") from exc
    return point


def read_position(delivery_id):
    try:
        raw = _client().get(_key(delivery_id))
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
        _client().delete(_key(delivery_id))
    except RedisError as exc:
        raise ExternalProviderError("Unable to end rider GPS sharing.") from exc
