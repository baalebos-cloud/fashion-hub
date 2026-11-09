"""Authenticated server-side address geocoding. No browser secret exposure."""
import logging

from fastapi import APIRouter, Depends, Query
from app.core.dependencies import get_current_user
from app.core.exceptions import ExternalProviderError, ValidationAppError
from app.integrations.maps.fallback import reverse_geocode_fallback
from app.core.config import settings
from app.integrations.maps import get_map_provider
from app.models.user import User

logger = logging.getLogger(__name__)
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
    try:
        return get_map_provider().reverse_geocode(latitude, longitude)
    except ExternalProviderError as exc:
        # Visible in the server logs, so a key or API-restriction problem with Google is easy to find.
        # The message carries Google's status and reason only: never the key or the coordinates.
        logger.warning("google_reverse_geocoding_failed reason=%s", str(exc)[:300])
        if not settings.GEOCODING_FALLBACK_URL:
            raise
        return reverse_geocode_fallback(latitude, longitude)
