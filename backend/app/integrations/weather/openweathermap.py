"""OpenWeatherMap implementation of WeatherProvider.
Docs: https://openweathermap.org/api/one-call-3"""
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError
from app.integrations.weather.base import WeatherProvider, WeatherSnapshot

BASE_URL = "https://api.openweathermap.org/data/3.0/onecall"


class OpenWeatherMapProvider(WeatherProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.WEATHER_API_KEY

    def _fetch(self, latitude: float, longitude: float) -> dict:
        try:
            response = httpx.get(
                BASE_URL,
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "appid": self.api_key,
                    "units": "metric",
                    "exclude": "minutely,alerts",
                },
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"OpenWeatherMap request failed: {exc}") from exc

    def get_current(self, *, latitude: float, longitude: float) -> WeatherSnapshot:
        data = self._fetch(latitude, longitude)
        current = data["current"]
        weather = current["weather"][0]
        return WeatherSnapshot(
            condition=weather["main"],
            description=weather["description"],
            temperature_celsius=current["temp"],
            feels_like_celsius=current["feels_like"],
            precipitation_probability=data.get("hourly", [{}])[0].get("pop"),
            wind_speed_kmh=current.get("wind_speed", 0) * 3.6,
            icon_code=weather.get("icon"),
            observed_at=datetime.fromtimestamp(current["dt"], tz=timezone.utc).isoformat(),
        )

    def get_forecast_at(self, *, latitude: float, longitude: float, target_time: str) -> WeatherSnapshot:
        data = self._fetch(latitude, longitude)
        target_ts = datetime.fromisoformat(target_time.replace("Z", "+00:00")).timestamp()

        # Pick the hourly forecast entry closest to the requested time.
        hourly = data.get("hourly", [])
        if not hourly:
            return self.get_current(latitude=latitude, longitude=longitude)

        closest = min(hourly, key=lambda entry: abs(entry["dt"] - target_ts))
        weather = closest["weather"][0]
        return WeatherSnapshot(
            condition=weather["main"],
            description=weather["description"],
            temperature_celsius=closest["temp"],
            feels_like_celsius=closest["feels_like"],
            precipitation_probability=closest.get("pop"),
            wind_speed_kmh=closest.get("wind_speed", 0) * 3.6,
            icon_code=weather.get("icon"),
            observed_at=datetime.fromtimestamp(closest["dt"], tz=timezone.utc).isoformat(),
        )
