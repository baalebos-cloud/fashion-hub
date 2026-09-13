from sqlalchemy.orm import Session
from app.models.professional import Professional


class ProfessionalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, professional_id):
        return self.db.get(Professional, professional_id)

    def list_verified(self, *, professional_type: str | None = None, offset: int = 0, limit: int = 20):
        query = self.db.query(Professional).filter(Professional.is_verified.is_(True))
        if professional_type:
            query = query.filter(Professional.professional_type == professional_type)
        return query.offset(offset).limit(limit).all()
