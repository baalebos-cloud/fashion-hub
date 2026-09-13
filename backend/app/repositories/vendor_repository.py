from sqlalchemy.orm import Session
from app.models.vendor import Vendor


class VendorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, vendor_id):
        return self.db.get(Vendor, vendor_id)

    def list_verified(self, *, offset: int = 0, limit: int = 20):
        return self.db.query(Vendor).filter(Vendor.is_verified.is_(True)).offset(offset).limit(limit).all()
