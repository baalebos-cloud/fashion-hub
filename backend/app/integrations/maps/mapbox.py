"""Mapbox implementation of MapProvider (Geocoding + Directions/Matrix APIs)."""
import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError
from app.integrations.maps.base import DistanceResult, GeocodeResult, MapProvider


class MapboxProvider(MapProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.MAPS_API_KEY

    def geocode(self, address: str) -> GeocodeResult:
        try:
            response = httpx.get(
                f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json",
                params={"access_token": self.api_key, "limit": 1},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("features"):
                raise ExternalProviderError("No geocoding results for address.")
            feature = data["features"][0]
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"Mapbox geocode failed: {exc}") from exc

        context = {c["id"].split(".")[0]: c["text"] for c in feature.get("context", [])}
        lng, lat = feature["center"]
        return GeocodeResult(
            latitude=lat,
            longitude=lng,
            formatted_address=feature.get("place_name", address),
            city=context.get("place"),
            state_region=context.get("region"),
            country=context.get("country"),
            postal_code=context.get("postcode"),
        )

    def reverse_geocode(self, latitude: float, longitude: float) -> GeocodeResult:
        try:
            response = httpx.get(
                f"https://api.mapbox.com/geocoding/v5/mapbox.places/{longitude},{latitude}.json",
                params={"access_token": self.api_key, "limit": 1},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("features"):
                raise ExternalProviderError("No reverse geocoding results for coordinates.")
            feature = data["features"][0]
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"Mapbox reverse_geocode failed: {exc}") from exc

        context = {c["id"].split(".")[0]: c["text"] for c in feature.get("context", [])}
        return GeocodeResult(
            latitude=latitude,
            longitude=longitude,
            formatted_address=feature.get("place_name", ""),
            city=context.get("place"),
            state_region=context.get("region"),
            country=context.get("country"),
            postal_code=context.get("postcode"),
        )

    def calculate_distance(
        self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
    ) -> DistanceResult:
        try:
            response = httpx.get(
                f"https://api.mapbox.com/directions/v5/mapbox/driving/"
                f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}",
                params={"access_token": self.api_key, "overview": "false"},
                timeout=10.0,
            )
            response.raise_for_status()
            route = response.json()["routes"][0]
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"Mapbox calculate_distance failed: {exc}") from exc

        return DistanceResult(distance_meters=route["distance"], duration_seconds=route["duration"])
