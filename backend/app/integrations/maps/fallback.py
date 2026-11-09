"""Secondary reverse geocoding with shared Redis caching and rate limiting.

Public Nominatim is opt-in and must respect OSMF's usage policy:
https://operations.osmfoundation.org/policies/nominatim/
"""
import json
import logging

import httpx
from redis import Redis

from app.core.config import settings
from app.core.exceptions import ExternalProviderError
from app.integrations.maps.base import GeocodeResult
from app.integrations.maps.nigeria_address import parse_nominatim_reverse

logger = logging.getLogger(__name__)


def reverse_geocode_fallback(latitude: float, longitude: float) -> GeocodeResult:
    base_url = (settings.GEOCODING_FALLBACK_URL or "").rstrip("/")
    contact = settings.GEOCODING_CONTACT_EMAIL
    if not base_url.startswith("https://") or not contact or "@" not in contact:
        raise ExternalProviderError("Secondary geocoding is not configured.")
    cache_key = f"geocoding:reverse:v2:{latitude:.5f}:{longitude:.5f}"
    try:
        redis = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        cached = redis.get(cache_key)
        if cached:
            return GeocodeResult(**json.loads(cached))
        # Distributed throttle across all Railway instances. Never bypass the
        # quota on Redis failure; 2 seconds between *started* requests.
        if not redis.set("geocoding:nominatim:global-rate", "1", nx=True, ex=2):
            raise ExternalProviderError("Secondary geocoding is rate limited.")
    except ExternalProviderError:
        raise
    except Exception as exc:
        logger.warning("geocoding_fallback_cache_unavailable type=%s", type(exc).__name__)
        raise ExternalProviderError("Secondary geocoding rate limiter unavailable.") from exc

    try:
        response = httpx.get(
            base_url + "/reverse",
            params={"format": "json", "lat": latitude, "lon": longitude, "addressdetails": 1},
            headers={"User-Agent": f"FashionHub/1.0 (contact: {contact})",
                     "Accept": "application/json"},
            timeout=8.0,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not data.get("display_name"):
            raise ExternalProviderError("Secondary geocoding found no address.")
        result = parse_nominatim_reverse(data, latitude, longitude)
        redis.setex(cache_key, 604800, json.dumps(result.__dict__))
        return result
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        logger.warning("geocoding_fallback_failed type=%s", type(exc).__name__)
        raise ExternalProviderError("Secondary reverse geocoding failed.") from exc
