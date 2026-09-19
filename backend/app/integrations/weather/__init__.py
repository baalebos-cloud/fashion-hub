"""Factory for resolving the configured WeatherProvider."""
from functools import lru_cache

from app.core.config import settings
from app.integrations.weather.base import WeatherProvider
from app.integrations.weather.openweathermap import OpenWeatherMapProvider

_PROVIDERS = {
    "openweathermap": OpenWeatherMapProvider,
}


@lru_cache
def get_weather_provider() -> WeatherProvider:
    provider_cls = _PROVIDERS.get(settings.WEATHER_PROVIDER)
    if provider_cls is None:
        raise ValueError(f"Unknown WEATHER_PROVIDER '{settings.WEATHER_PROVIDER}'")
    return provider_cls()
