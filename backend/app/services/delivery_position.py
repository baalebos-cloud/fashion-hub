"""Privacy-scoped rider GPS, requiring explicit sharing consent.

A random in-memory browser token authorizes the rider's temporary telemetry. One Redis script
atomically checks consent, rejects stale, replayed, out-of-order and too-frequent points, stores
the point and extends the consent while the rider keeps sharing. Stopping sharing (or delivery,
release or cancellation) atomically revokes consent and erases the point.

Freshness is decided by the age of the rider's own GPS fix, not by when we last looked:
    live        fix ≤ POSITION_LIVE_SECONDS old
    delayed     fix ≤ POSITION_DELAYED_SECONDS old
    last_known  older, kept up to POSITION_LAST_KNOWN_SECONDS, shown as "last seen", never as current
After that the point is gone. Nothing is written to the database or to logs; positions live only
in Redis with a TTL. The rider's device can also report "permission_denied" or "unavailable" so
customers and dispatchers see why there is no location.
"""
import json
from datetime import datetime, timedelta, timezone

from redis import Redis
from redis.exceptions import RedisError

from app.core.exceptions import ExternalProviderError, ForbiddenError, ValidationAppError

from app.core.config import settings

POSITION_LIVE_SECONDS = 30
POSITION_DELAYED_SECONDS = 90
POSITION_LAST_KNOWN_SECONDS = 600
POSITION_TTL_SECONDS = POSITION_LAST_KNOWN_SECONDS
SESSION_TTL_SECONDS = 3600          # consent lapses after an hour without any update
MIN_INTERVAL_SECONDS = 3            # the server ignores points closer together than this
MAX_FIX_AGE_SECONDS = 120           # a fix older than this on arrival is rejected
MAX_CLOCK_SKEW_SECONDS = 30         # a fix this far in the future is rejected
DEVICE_STATE_TTL_SECONDS = 300
DEVICE_STATES = {"permission_denied", "unavailable", "paused"}

# KEYS: consent, point, last_fix   ARGV: token, point_json, fix_epoch, ttl, session_ttl, min_interval
_PUBLISH_IF_CONSENTED = """
local token = redis.call('GET', KEYS[1])
if token ~= ARGV[1] then return 0 end
local last = tonumber(redis.call('GET', KEYS[3]) or '0')
local fix = tonumber(ARGV[3])
if fix <= last then return -1 end
if fix - last < tonumber(ARGV[6]) then return -2 end
redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[4])
redis.call('SET', KEYS[3], ARGV[3], 'EX', ARGV[4])
redis.call('EXPIRE', KEYS[1], ARGV[5])
return 1
"""


def _client():
    return Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)


def _key(delivery_id, suffix):
    return "delivery:gps:" + str(delivery_id) + ":" + suffix


def start_sharing(delivery_id):
    import secrets
    share_token = secrets.token_urlsafe(32)
    try:
        client = _client()
        client.set(_key(delivery_id, "consent"), share_token, ex=SESSION_TTL_SECONDS)
        client.delete(_key(delivery_id, "device_state"))
    except RedisError as exc:
        raise ExternalProviderError("GPS sharing is temporarily unavailable.") from exc
    return {"share_token": share_token}


def _fix_time(recorded_at: datetime | None) -> datetime:
    now = datetime.now(timezone.utc)
    if recorded_at is None:
        return now  # older clients: the server's clock stands in for the fix time
    fix = recorded_at if recorded_at.tzinfo else recorded_at.replace(tzinfo=timezone.utc)
    if fix > now + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS):
        raise ValidationAppError("The GPS fix time is in the future. Check the phone's clock.")
    if fix < now - timedelta(seconds=MAX_FIX_AGE_SECONDS):
        raise ValidationAppError("This GPS fix is too old to share.")
    return fix


def save_position(delivery_id, *, share_token, latitude: float, longitude: float, accuracy_m: float,
                  recorded_at: datetime | None = None, speed_mps: float | None = None):
    fix = _fix_time(recorded_at)
    point = {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy_m": accuracy_m,
        "recorded_at": fix.isoformat(),
        "received_at": datetime.now(timezone.utc).isoformat(),
        **({"speed_mps": round(speed_mps, 1)} if speed_mps is not None else {}),
    }
    try:
        result = _client().eval(
            _PUBLISH_IF_CONSENTED, 3,
            _key(delivery_id, "consent"), _key(delivery_id, "point"), _key(delivery_id, "last_fix"),
            share_token, json.dumps(point), f"{fix.timestamp():.3f}", POSITION_TTL_SECONDS,
            SESSION_TTL_SECONDS, MIN_INTERVAL_SECONDS,
        )
    except RedisError as exc:
        raise ExternalProviderError("Rider GPS updates are temporarily unavailable.") from exc
    if result == 0:
        raise ForbiddenError("GPS sharing is not active. Start sharing again.")
    if result == -1:
        raise ValidationAppError("This GPS point is older than one already shared.")
    if result == -2:
        return {**point, "accepted": False}  # too soon after the last one: ignored, not an error
    try:
        _client().delete(_key(delivery_id, "device_state"))
    except RedisError:
        pass
    return {**point, "accepted": True}


def report_device_state(delivery_id, *, share_token: str, state: str) -> None:
    """The rider's phone says why it can't send a location (permission denied, no signal...)."""
    if state not in DEVICE_STATES:
        raise ValidationAppError("Unknown location state.")
    try:
        client = _client()
        if client.get(_key(delivery_id, "consent")) != share_token.encode():
            raise ForbiddenError("GPS sharing is not active. Start sharing again.")
        client.set(_key(delivery_id, "device_state"), state, ex=DEVICE_STATE_TTL_SECONDS)
    except RedisError as exc:
        raise ExternalProviderError("Rider GPS updates are temporarily unavailable.") from exc


def freshness(point: dict | None, now: datetime | None = None) -> tuple[str, int | None]:
    if not point:
        return "unavailable", None
    try:
        fix = datetime.fromisoformat(point["recorded_at"])
    except (KeyError, ValueError, TypeError):
        return "unavailable", None
    if fix.tzinfo is None:
        fix = fix.replace(tzinfo=timezone.utc)
    age = max(0, int(((now or datetime.now(timezone.utc)) - fix).total_seconds()))
    if age <= POSITION_LIVE_SECONDS:
        return "live", age
    if age <= POSITION_DELAYED_SECONDS:
        return "delayed", age
    if age <= POSITION_LAST_KNOWN_SECONDS:
        return "last_known", age
    return "unavailable", age


def read_position(delivery_id):
    """The latest point with its freshness, or None. Callers must not present a `last_known`
    point as the rider's current position."""
    try:
        client = _client()
        raw = client.get(_key(delivery_id, "point"))
        device_state = client.get(_key(delivery_id, "device_state"))
        sharing = bool(client.exists(_key(delivery_id, "consent")))
    except RedisError:
        return None
    if not raw:
        return None
    try:
        payload = json.loads(raw)
        if not all(k in payload for k in ("latitude", "longitude", "accuracy_m", "recorded_at")):
            return None
    except (ValueError, TypeError):
        return None
    state, age = freshness(payload)
    if state == "unavailable":
        return None
    payload.update(freshness=state, age_seconds=age, sharing=sharing,
                   device_state=device_state.decode() if device_state else None)
    return payload


def tracking_status(delivery_id) -> dict:
    """Location state without coordinates, for lists and public views."""
    try:
        client = _client()
        sharing = bool(client.exists(_key(delivery_id, "consent")))
        device_state = client.get(_key(delivery_id, "device_state"))
        raw = client.get(_key(delivery_id, "point"))
    except RedisError:
        return {"state": "unknown", "age_seconds": None, "sharing": False, "device_state": None}
    state, age = freshness(json.loads(raw) if raw else None)
    device = device_state.decode() if device_state else None
    if device == "permission_denied":
        state = "permission_denied"
    elif state == "unavailable" and not sharing:
        state = "not_sharing"
    return {"state": state, "age_seconds": age, "sharing": sharing, "device_state": device}


def clear_position(delivery_id):
    try:
        client = _client()
        with client.pipeline(transaction=True) as pipe:
            pipe.delete(_key(delivery_id, "consent"), _key(delivery_id, "point"),
                        _key(delivery_id, "last_fix"), _key(delivery_id, "device_state"))
            pipe.execute()
    except RedisError as exc:
        raise ExternalProviderError("Unable to end rider GPS sharing.") from exc
