"""
Weather-at-delivery lookups, cached in Redis so a busy tracking page
polling every 15s (see frontend hooks/use-tracking.ts) doesn't hammer the
provider -- weather doesn't change meaningfully faster than every ~15
minutes, so that's the cache TTL.
"""
import json

from app.core.redis import get_redis_client
from app.integrations.weather import get_weather_provider
from app.integrations.weather.base import WeatherSnapshot

CACHE_TTL_SECONDS = 15 * 60


class WeatherService:
    def __init__(self):
        self.provider = get_weather_provider()
        self.redis = get_redis_client()

    def get_current_weather(self, *, latitude: float, longitude: float) -> WeatherSnapshot:
        cache_key = f"weather:current:{round(latitude, 3)}:{round(longitude, 3)}"
        cached = self.redis.get(cache_key)
        if cached:
            return WeatherSnapshot(**json.loads(cached))

        snapshot = self.provider.get_current(latitude=latitude, longitude=longitude)
        self.redis.set(cache_key, json.dumps(snapshot.__dict__), ex=CACHE_TTL_SECONDS)
        return snapshot

    def get_forecast_for_delivery(self, *, latitude: float, longitude: float, eta_iso: str) -> WeatherSnapshot:
        """Forecast at the delivery destination for the order's estimated
        arrival time -- this is what answers 'will it be raining when my
        order gets here.'"""
        cache_key = f"weather:forecast:{round(latitude, 3)}:{round(longitude, 3)}:{eta_iso[:13]}"  # hour-bucketed
        cached = self.redis.get(cache_key)
        if cached:
            return WeatherSnapshot(**json.loads(cached))

        snapshot = self.provider.get_forecast_at(latitude=latitude, longitude=longitude, target_time=eta_iso)
        self.redis.set(cache_key, json.dumps(snapshot.__dict__), ex=CACHE_TTL_SECONDS)
        return snapshot

    def is_rain_expected(self, snapshot: WeatherSnapshot) -> bool:
        """Simple, explicit rule the frontend can rely on for a 'bring an
        umbrella' / rain-delay warning, rather than re-deriving it from
        raw condition strings on the client."""
        if snapshot.condition.lower() in ("rain", "drizzle", "thunderstorm"):
            return True
        return bool(snapshot.precipitation_probability and snapshot.precipitation_probability >= 0.4)
