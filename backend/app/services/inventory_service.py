"""Vendor-owned additive restock shares the checkout inventory row lock."""
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.inventory import Inventory
from app.models.product_variant import ProductVariant
from app.models.vendor_product import VendorProduct
from app.services.vendor_catalog_service import VendorCatalogService


class InventoryService:
    def __init__(self, db):
        self.db = db

    def owned_query(self, user_id):
        vendor = VendorCatalogService(self.db).owned_vendor(user_id)
        return self.db.query(Inventory).join(ProductVariant, ProductVariant.id == Inventory.product_variant_id).join(
            VendorProduct, VendorProduct.id == ProductVariant.product_id).filter(VendorProduct.vendor_id == vendor.id)

    def list(self, user_id, *, offset=0, limit=20):
        return self.owned_query(user_id).order_by(Inventory.product_variant_id).offset(offset).limit(limit).all()

    def restock(self, product_variant_id, *, owner_user_id, quantity_to_add):
        if type(quantity_to_add) is not int or not 1 <= quantity_to_add <= 1000000000:
            raise ValidationAppError('Restock quantity must be between 1 and 1000000000.')
        inventory = self.owned_query(owner_user_id).filter(Inventory.product_variant_id == product_variant_id).with_for_update(of=Inventory).populate_existing().first()
        if not inventory:
            raise NotFoundError('Inventory record not found.')
        if inventory.quantity_available + inventory.quantity_reserved + quantity_to_add > 1000000000:
            raise ConflictError('Restock exceeds the supported inventory total.')
        inventory.quantity_available += quantity_to_add
        self.db.commit()
        return inventory
