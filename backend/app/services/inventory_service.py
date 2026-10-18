"""Vendor-owned additive restock shares the checkout inventory row lock."""
import re
from sqlalchemy.exc import IntegrityError
from app.models.inventory_restock import InventoryRestock
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
        rows = self.owned_query(user_id).add_columns(VendorProduct.name, ProductVariant.sku).order_by(Inventory.product_variant_id).offset(offset).limit(limit).all()
        return [self.describe(inv, name, sku) for inv, name, sku in rows]

    @staticmethod
    def describe(inv, name, sku):
        return dict(id=inv.id, product_variant_id=inv.product_variant_id, product_name=name, sku=sku,
                    quantity_available=inv.quantity_available, quantity_reserved=inv.quantity_reserved)

    def restock(self, product_variant_id, *, owner_user_id, quantity_to_add, idempotency_key):
        if type(quantity_to_add) is not int or not 1 <= quantity_to_add <= 1000000000:
            raise ValidationAppError('Restock quantity must be between 1 and 1000000000.')
        if not isinstance(idempotency_key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", idempotency_key):
            raise ValidationAppError("A valid restock idempotency key is required.")
        inventory = self.owned_query(owner_user_id).filter(Inventory.product_variant_id == product_variant_id).with_for_update(of=Inventory).populate_existing().first()
        if not inventory:
            raise NotFoundError('Inventory record not found.')
        previous = self.db.query(InventoryRestock).filter_by(idempotency_key=idempotency_key).first()
        if previous:
            self._assert_replay(previous, owner_user_id, product_variant_id, quantity_to_add)
        elif inventory.quantity_available + inventory.quantity_reserved + quantity_to_add > 1000000000:
            raise ConflictError('Restock exceeds the supported inventory total.')
        else:
            try:
                inventory.quantity_available += quantity_to_add
                self.db.add(InventoryRestock(product_variant_id=product_variant_id, actor_user_id=owner_user_id,
                                             quantity=quantity_to_add, idempotency_key=idempotency_key))
                self.db.commit()
            except IntegrityError:
                self.db.rollback()
                previous = self.db.query(InventoryRestock).filter_by(idempotency_key=idempotency_key).first()
                if not previous:
                    raise
                self._assert_replay(previous, owner_user_id, product_variant_id, quantity_to_add)
                self.db.refresh(inventory)
            except Exception:
                self.db.rollback()
                raise
        variant = self.db.get(ProductVariant, inventory.product_variant_id)
        product = self.db.get(VendorProduct, variant.product_id)
        return self.describe(inventory, product.name, variant.sku)


    @staticmethod
    def _assert_replay(previous, owner_user_id, variant_id, quantity):
        if (str(previous.actor_user_id) != str(owner_user_id) or str(previous.product_variant_id) != str(variant_id)
            or previous.quantity != quantity):
            raise ConflictError('Idempotency key is already used for a different restock.')
