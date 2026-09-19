"""
WeatherProvider interface. Services/routes depend only on this, never a
concrete provider, so swapping OpenWeatherMap for another provider is a
change in this folder plus one env var -- same pattern as
integrations/maps, integrations/payments, etc.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class WeatherSnapshot:
    condition: str          # e.g. "Rain", "Clear", "Clouds"
    description: str        # e.g. "light rain"
    temperature_celsius: float
    feels_like_celsius: float
    precipitation_probability: float | None  # 0.0-1.0, when the provider supports it
    wind_speed_kmh: float | None
    icon_code: str | None   # provider-specific icon identifier
    observed_at: str        # ISO 8601, when this reading/forecast point is for


class WeatherProvider(ABC):
    @abstractmethod
    def get_current(self, *, latitude: float, longitude: float) -> WeatherSnapshot:
        """Current conditions at a point -- used for 'live' delivery tracking."""
        raise NotImplementedError

    @abstractmethod
    def get_forecast_at(self, *, latitude: float, longitude: float, target_time: str) -> WeatherSnapshot:
        """Best-available forecast for a specific future ISO 8601 timestamp
        -- used to show 'expected weather at estimated delivery time'."""
        raise NotImplementedError
