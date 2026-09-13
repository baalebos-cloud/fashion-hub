"""Shared professional profile operations for tailors and designers."""
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError


class ProfessionalService:
    def __init__(self, db: Session):
        self.db = db

    def update_profile(self, professional_id, *, actor_user_id, **fields):
        from app.models.professional import Professional

        professional = self.db.get(Professional, professional_id)
        if not professional:
            raise NotFoundError("Professional profile not found.")
        if str(professional.user_id) != str(actor_user_id):
            raise ForbiddenError("You do not have permission to modify this profile.")
        for key, value in fields.items():
            if hasattr(professional, key) and value is not None:
                setattr(professional, key, value)
        self.db.commit()
        self.db.refresh(professional)
        return professional
