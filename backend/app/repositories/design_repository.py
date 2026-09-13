from sqlalchemy.orm import Session
from app.models.design import Design


class DesignRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_professional(self, professional_id, *, offset: int = 0, limit: int = 20):
        return (
            self.db.query(Design)
            .filter(Design.professional_id == professional_id, Design.is_published.is_(True))
            .offset(offset)
            .limit(limit)
            .all()
        )
