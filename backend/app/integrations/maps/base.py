"""
MapProvider interface for geocoding, reverse geocoding, distance/routing.
Business logic (location_service, distance_service) depends only on this
interface, never on GoogleMapsProvider/MapboxProvider directly.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GeocodeResult:
    latitude: float
    longitude: float
    formatted_address: str
    city: str | None
    state_region: str | None
    country: str | None
    postal_code: str | None
    # The parts a Nigerian address form needs, when the provider knows them (all optional):
    street: str | None = None            # "12 Admiralty Way"
    area: str | None = None              # neighbourhood / district, e.g. "Lekki Phase 1"
    lga: str | None = None               # local government area, e.g. "Eti-Osa"
    landmark: str | None = None          # a named place at or near the point
    nearest_bus_stop: str | None = None


@dataclass
class DistanceResult:
    distance_meters: float
    duration_seconds: float


class MapProvider(ABC):
    @abstractmethod
    def geocode(self, address: str) -> GeocodeResult:
        """Address -> coordinates."""
        raise NotImplementedError

    @abstractmethod
    def reverse_geocode(self, latitude: float, longitude: float) -> GeocodeResult:
        """Coordinates -> address."""
        raise NotImplementedError

    @abstractmethod
    def calculate_distance(
        self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
    ) -> DistanceResult:
        """Driving distance/duration between two points, used for delivery
        fee estimation and ETA."""
        raise NotImplementedError
