"""
Location CRUD + privacy-aware read access. Precise coordinates are only
exposed to users who need them for fulfillment (the assigned delivery
partner, the two parties to an order); everyone else gets a
truncated/approximate location (e.g. rounded to ~1km) via `to_public_view`.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.services.spatial_discovery import validated_search


class LocationService:
    def __init__(self, db: Session):
        self.db = db

    def create_location(self, *, latitude: float, longitude: float, location_type: str, **address_fields):
        from app.models.location import Location

        lat, lon, _, _, _ = validated_search(latitude=latitude, longitude=longitude)
        location = Location(
            latitude=lat, longitude=lon, location_type=location_type,
            geom=func.ST_GeogFromText(f"SRID=4326;POINT({lon} {lat})"),
            **address_fields,
        )
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)
        return location

    @staticmethod
    def to_public_view(location) -> dict:
        """Truncates precision to ~2 decimal places (~1.1km) for public
        listing pages (e.g. 'tailors near you' before an order exists)."""
        return {
            "latitude": round(float(location.latitude), 2) if location.latitude is not None else None,
            "longitude": round(float(location.longitude), 2) if location.longitude is not None else None,
            "city": location.city,
            "state_region": location.state_region,
            "country": location.country,
        }
