"""
Inventory read/write. Authoritative stock decrements happen inside
checkout_service's transaction (with row locks); this service handles
vendor-facing stock updates (restocking, threshold changes) and read-only
availability checks used by product listing pages.
"""
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationAppError


class InventoryService:
    def __init__(self, db: Session):
        self.db = db

    def restock(self, product_variant_id, *, quantity_to_add: int):
        from app.models.inventory import Inventory

        if quantity_to_add < 1:
            raise ValidationAppError("quantity_to_add must be positive.")
        inventory = self.db.query(Inventory).filter(Inventory.product_variant_id == product_variant_id).first()
        if not inventory:
            raise NotFoundError("Inventory record not found for this product variant.")
        inventory.quantity_available += quantity_to_add
        self.db.commit()
        return inventory
