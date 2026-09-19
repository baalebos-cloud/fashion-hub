"""
/weather

Standalone weather lookups by coordinate -- used by the delivery partner's
own "what's it like where I am" view and anywhere else a raw lat/lng is
available. For weather AT A SPECIFIC ORDER'S delivery destination, see
GET /orders/{order_id}/weather in orders.py, which additionally resolves
the order's delivery address and (if available) folds in the live ETA so
the forecast is for the actual expected arrival time, not just "now."
"""
from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.weather import WeatherResponse
from app.services.weather_service import WeatherService

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("/current", response_model=WeatherResponse)
def get_current_weather(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    _current_user: User = Depends(get_current_user),
):
    service = WeatherService()
    snapshot = service.get_current_weather(latitude=latitude, longitude=longitude)
    return WeatherResponse(**snapshot.__dict__, rain_expected=service.is_rain_expected(snapshot))
