from sqlalchemy.orm import Session
from app.models.vendor_product import VendorProduct


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id):
        return self.db.get(VendorProduct, product_id)

    def list_for_vendor(self, vendor_id, *, offset: int = 0, limit: int = 20):
        return (
            self.db.query(VendorProduct)
            .filter(VendorProduct.vendor_id == vendor_id, VendorProduct.is_active.is_(True))
            .offset(offset)
            .limit(limit)
            .all()
        )
