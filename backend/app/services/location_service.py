"""
Location CRUD + privacy-aware read access. Precise coordinates are only
exposed to users who need them for fulfillment (the assigned delivery
partner, the two parties to an order); everyone else gets a
truncated/approximate location (e.g. rounded to ~1km) via `to_public_view`.
"""
from sqlalchemy.orm import Session


class LocationService:
    def __init__(self, db: Session):
        self.db = db

    def create_location(self, *, latitude: float, longitude: float, location_type: str, **address_fields):
        from app.models.location import Location

        location = Location(latitude=latitude, longitude=longitude, location_type=location_type, **address_fields)
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)
        return location

    @staticmethod
    def to_public_view(location) -> dict:
        """Truncates precision to ~2 decimal places (~1.1km) for public
        listing pages (e.g. 'tailors near you' before an order exists)."""
        return {
            "latitude": round(float(location.latitude), 2),
            "longitude": round(float(location.longitude), 2),
            "city": location.city,
            "state_region": location.state_region,
            "country": location.country,
        }
