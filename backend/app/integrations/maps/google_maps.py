"""Google Maps Platform implementation of MapProvider (Geocoding + Distance
Matrix APIs)."""
import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError
import math

from app.integrations.maps.base import DistanceResult, GeocodeResult, MapProvider
from app.integrations.maps.nigeria_address import parse_google_reverse

# Places that are areas, not landmarks a rider can look for.
_AREA_TYPES = {"locality", "sublocality", "political", "route", "neighborhood", "administrative_area_level_1",
               "administrative_area_level_2", "country", "postal_code", "plus_code"}


def _km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


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
        if not self.api_key or not self.api_key.strip():
            raise ExternalProviderError("Google reverse geocoding is not configured.")
        try:
            response = httpx.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"latlng": f"{latitude},{longitude}", "key": self.api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "OK" or not data.get("results"):
                # Google's own reason, e.g. "This API key is not authorized to use this service" (no key in it).
                reason = str(data.get("error_message") or "")[:200]
                raise ExternalProviderError(f"Google reverse geocoding unavailable ({data.get('status', 'UNKNOWN')})"
                                            + (f": {reason}" if reason else "."))
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"Google reverse_geocode failed: {exc}") from exc

        found = parse_google_reverse(data["results"], latitude, longitude)
        found.nearest_bus_stop = self._nearby_name(latitude, longitude, type_="bus_station", rank_by_distance=True)
        if not found.landmark:
            found.landmark = self._nearby_name(latitude, longitude, radius=250)
        return found

    def _nearby_name(self, latitude: float, longitude: float, *, type_: str | None = None,
                     rank_by_distance: bool = False, radius: int = 0, max_km: float = 1.5) -> str | None:
        """Best effort: the closest named place (Places Nearby Search). Never fails the lookup: if the
        Places API isn't enabled for this key, or nothing is near, the field is just left empty."""
        params = {"location": f"{latitude},{longitude}", "key": self.api_key}
        if type_:
            params["type"] = type_
        if rank_by_distance:
            params["rankby"] = "distance"
        else:
            params["radius"] = radius
        try:
            response = httpx.get("https://maps.googleapis.com/maps/api/place/nearbysearch/json", params=params, timeout=6.0)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            return None
        if data.get("status") != "OK":
            return None
        for place in data.get("results") or []:
            types = set(place.get("types") or [])
            if not type_ and (types & _AREA_TYPES or not types & {"point_of_interest", "establishment"}):
                continue
            where = (place.get("geometry") or {}).get("location") or {}
            if "lat" in where and _km(latitude, longitude, where["lat"], where["lng"]) > max_km:
                continue
            name = " ".join(str(place.get("name") or "").split())
            if name:
                return name
        return None

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
