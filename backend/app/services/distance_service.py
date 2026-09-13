"""Distance/ETA calculations, backed by the configured MapProvider and
PostGIS for bulk nearest-neighbor queries."""
from sqlalchemy.orm import Session

from app.integrations.maps import get_map_provider


class DistanceService:
    def __init__(self, db: Session):
        self.db = db
        self.map_provider = get_map_provider()

    def calculate_delivery_fee(self, *, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, base_fee: float, per_km_rate: float) -> float:
        result = self.map_provider.calculate_distance(origin_lat, origin_lng, dest_lat, dest_lng)
        distance_km = result.distance_meters / 1000
        return round(base_fee + (distance_km * per_km_rate), 2)

    def find_nearby_professionals(self, *, latitude: float, longitude: float, radius_km: float = 10, limit: int = 20):
        """
        Uses PostGIS ST_DWithin on Location.geom for an efficient
        nearest-neighbor query. Example (to be run via raw SQL/GeoAlchemy):

            SELECT p.* FROM professionals p
            JOIN locations l ON p.location_id = l.id
            WHERE ST_DWithin(l.geom, ST_MakePoint(:lng, :lat)::geography, :radius_m)
            ORDER BY l.geom <-> ST_MakePoint(:lng, :lat)::geography
            LIMIT :limit;
        """
        raise NotImplementedError("Wire in the ST_DWithin query shown in this docstring via SQLAlchemy/GeoAlchemy2.")
