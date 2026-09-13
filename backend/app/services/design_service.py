"""Design/portfolio CRUD for tailors and designers."""
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError


class DesignService:
    def __init__(self, db: Session):
        self.db = db

    def create_design(self, *, professional_id, title: str, description: str | None, base_price: float, category_id=None):
        from app.models.design import Design

        design = Design(
            professional_id=professional_id,
            title=title,
            description=description,
            base_price=base_price,
            category_id=category_id,
        )
        self.db.add(design)
        self.db.commit()
        self.db.refresh(design)
        return design

    def update_design(self, design_id, *, actor_professional_id, **fields):
        from app.models.design import Design

        design = self.db.get(Design, design_id)
        if not design:
            raise NotFoundError("Design not found.")
        if str(design.professional_id) != str(actor_professional_id):
            raise ForbiddenError("You do not have permission to modify this design.")
        for key, value in fields.items():
            setattr(design, key, value)
        self.db.commit()
        return design
