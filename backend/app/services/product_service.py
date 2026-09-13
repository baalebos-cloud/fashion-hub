"""Vendor product + variant CRUD."""
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError


class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def create_product(self, *, vendor_id, name: str, description: str | None, base_price: float, category_id=None):
        from app.models.inventory import Inventory
        from app.models.product_variant import ProductVariant
        from app.models.vendor_product import VendorProduct

        product = VendorProduct(vendor_id=vendor_id, name=name, description=description, base_price=base_price, category_id=category_id)
        self.db.add(product)
        self.db.flush()

        # Every product gets a default variant so cart/checkout can always
        # reference a ProductVariant, even for vendors who don't need
        # multiple SKUs per product.
        default_variant = ProductVariant(product_id=product.id, sku=f"{product.id}-default", price=base_price)
        self.db.add(default_variant)
        self.db.flush()
        self.db.add(Inventory(product_variant_id=default_variant.id, quantity_available=0))
        self.db.commit()
        self.db.refresh(product)
        return product
