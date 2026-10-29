from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.models.professional import Professional
from app.models.user import User
from app.models.location import Location


class ProfessionalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, professional_id):
        return self.db.get(Professional, professional_id)

    def verified_query(self, *, professional_type=None, query=None, latitude=None, longitude=None, radius_km=10):
        result = self.db.query(Professional).join(User, User.id == Professional.user_id).filter(
            Professional.is_verified.is_(True), User.is_active.is_(True))
        if professional_type:
            result = result.filter(Professional.professional_type == professional_type)
        if query:
            pattern = '%' + query.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
            matching_locations = self.db.query(Location.id).filter(or_(
                Location.city.ilike(pattern, escape='\\'),
                Location.state_region.ilike(pattern, escape='\\'),
                Location.formatted_address.ilike(pattern, escape='\\'),
            ))
            result = result.filter(or_(
                Professional.business_name.ilike(pattern, escape='\\'),
                Professional.bio.ilike(pattern, escape='\\'),
                User.full_name.ilike(pattern, escape='\\'),
                Professional.location_id.in_(matching_locations),
            ))
        if latitude is not None and longitude is not None:
            # Coordinate columns are authoritative; older profiles may not have geom populated.
            distance = 6371 * func.acos(func.least(1.0, func.greatest(-1.0,
                func.sin(func.radians(latitude)) * func.sin(func.radians(Location.latitude)) +
                func.cos(func.radians(latitude)) * func.cos(func.radians(Location.latitude)) *
                func.cos(func.radians(Location.longitude) - func.radians(longitude)))))
            result = result.join(Location, Location.id == Professional.location_id).filter(distance <= radius_km)
        return result

    def list_verified(self, *, professional_type=None, offset=0, limit=20):
        return self.verified_query(professional_type=professional_type).order_by(Professional.id).offset(offset).limit(limit).all()
