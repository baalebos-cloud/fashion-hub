"""Thin service wrapping the configured MapProvider for geocode/reverse
geocode requests, with Redis caching to reduce provider API cost/latency."""
from app.core.redis import get_redis_client
from app.integrations.maps import get_map_provider


class GeocodingService:
    def __init__(self):
        self.map_provider = get_map_provider()
        self.redis = get_redis_client()

    def geocode(self, address: str):
        cache_key = f"geocode:{address.lower().strip()}"
        cached = self.redis.get(cache_key)
        if cached:
            import json
            return json.loads(cached)

        result = self.map_provider.geocode(address)
        payload = result.__dict__
        import json
        self.redis.set(cache_key, json.dumps(payload), ex=86400)  # cache 24h; addresses rarely move
        return payload

    def reverse_geocode(self, latitude: float, longitude: float):
        return self.map_provider.reverse_geocode(latitude, longitude).__dict__
