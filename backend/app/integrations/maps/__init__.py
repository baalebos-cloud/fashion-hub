"""Factory for resolving the configured MapProvider."""
from functools import lru_cache

from app.core.config import settings
from app.integrations.maps.base import MapProvider
from app.integrations.maps.google_maps import GoogleMapsProvider
from app.integrations.maps.mapbox import MapboxProvider

_PROVIDERS = {
    "google_maps": GoogleMapsProvider,
    "mapbox": MapboxProvider,
}


@lru_cache
def get_map_provider() -> MapProvider:
    provider_cls = _PROVIDERS.get(settings.MAP_PROVIDER)
    if provider_cls is None:
        raise ValueError(f"Unknown MAP_PROVIDER '{settings.MAP_PROVIDER}'")
    return provider_cls()
