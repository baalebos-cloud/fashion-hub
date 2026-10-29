"""Authenticated server-side address geocoding. No browser secret exposure."""
from fastapi import APIRouter, Depends, Query
from app.core.dependencies import get_current_user
from app.core.exceptions import ValidationAppError
from app.integrations.maps import get_map_provider
from app.models.user import User

router = APIRouter(prefix="/geocoding", tags=["Geocoding"])


@router.get("/geocode")
def geocode(address: str = Query(..., min_length=5, max_length=512),
            current_user: User = Depends(get_current_user)):
    if not address.strip():
        raise ValidationAppError("Enter an address to locate.")
    return get_map_provider().geocode(address)


@router.get("/reverse")
def reverse(latitude: float = Query(..., ge=-90, le=90),
            longitude: float = Query(..., ge=-180, le=180),
            current_user: User = Depends(get_current_user)):
    return get_map_provider().reverse_geocode(latitude, longitude)
