from sqlalchemy.orm import Session
from app.models.location import Location


class LocationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, location_id):
        return self.db.get(Location, location_id)
