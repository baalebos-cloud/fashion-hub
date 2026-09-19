from typing import Optional
from pydantic import BaseModel


class WeatherResponse(BaseModel):
    condition: str
    description: str
    temperature_celsius: float
    feels_like_celsius: float
    precipitation_probability: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    icon_code: Optional[str] = None
    observed_at: str
    rain_expected: bool
