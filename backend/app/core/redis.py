"""
Redis connection helper.

Used for: rate limiting, caching (e.g. nearby-tailor search results,
geocoding lookups), idempotency keys for webhooks, and Celery broker/backend
(configured separately in app/workers/celery_app.py).
"""
from functools import lru_cache

import redis

from app.core.config import settings


@lru_cache
def get_redis_client() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def check_redis_health() -> bool:
    try:
        return get_redis_client().ping()
    except Exception:
        return False


def acquire_idempotency_lock(key: str, ttl_seconds: int = 60) -> bool:
    """
    Atomic SET NX used to make webhook handlers idempotent.
    Returns True if this call acquired the lock (i.e. first time seeing `key`).
    Returns False if the key already exists (i.e. duplicate event).
    """
    client = get_redis_client()
    return bool(client.set(name=f"idempotency:{key}", value="1", nx=True, ex=ttl_seconds))
