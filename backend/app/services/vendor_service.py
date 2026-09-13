"""Vendor business profile management."""
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError


class VendorService:
    def __init__(self, db: Session):
        self.db = db

    def create_profile(self, *, user_id, business_name: str, business_description: str | None = None):
        from app.models.vendor import Vendor

        vendor = Vendor(user_id=user_id, business_name=business_name, business_description=business_description)
        self.db.add(vendor)
        self.db.commit()
        self.db.refresh(vendor)
        return vendor
