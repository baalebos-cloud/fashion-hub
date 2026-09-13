"""Google Maps Platform implementation of MapProvider (Geocoding + Distance
Matrix APIs)."""
import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError
from app.integrations.maps.base import DistanceResult, GeocodeResult, MapProvider


class GoogleMapsProvider(MapProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.MAPS_API_KEY

    def geocode(self, address: str) -> GeocodeResult:
        try:
            response = httpx.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": address, "key": self.api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("results"):
                raise ExternalProviderError("No geocoding results for address.")
            result = data["results"][0]
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"Google geocode failed: {exc}") from exc

        location = result["geometry"]["location"]
        components = {c["types"][0]: c["long_name"] for c in result["address_components"] if c["types"]}
        return GeocodeResult(
            latitude=location["lat"],
            longitude=location["lng"],
            formatted_address=result["formatted_address"],
            city=components.get("locality"),
            state_region=components.get("administrative_area_level_1"),
            country=components.get("country"),
            postal_code=components.get("postal_code"),
        )

    def reverse_geocode(self, latitude: float, longitude: float) -> GeocodeResult:
        try:
            response = httpx.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"latlng": f"{latitude},{longitude}", "key": self.api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("results"):
                raise ExternalProviderError("No reverse geocoding results for coordinates.")
            result = data["results"][0]
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"Google reverse_geocode failed: {exc}") from exc

        components = {c["types"][0]: c["long_name"] for c in result["address_components"] if c["types"]}
        return GeocodeResult(
            latitude=latitude,
            longitude=longitude,
            formatted_address=result["formatted_address"],
            city=components.get("locality"),
            state_region=components.get("administrative_area_level_1"),
            country=components.get("country"),
            postal_code=components.get("postal_code"),
        )

    def calculate_distance(
        self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
    ) -> DistanceResult:
        try:
            response = httpx.get(
                "https://maps.googleapis.com/maps/api/distancematrix/json",
                params={
                    "origins": f"{origin_lat},{origin_lng}",
                    "destinations": f"{dest_lat},{dest_lng}",
                    "key": self.api_key,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            element = response.json()["rows"][0]["elements"][0]
            if element["status"] != "OK":
                raise ExternalProviderError(f"Distance Matrix element status: {element['status']}")
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"Google calculate_distance failed: {exc}") from exc

        return DistanceResult(
            distance_meters=element["distance"]["value"], duration_seconds=element["duration"]["value"]
        )
