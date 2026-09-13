from sqlalchemy.orm import Session
from app.models.inventory import Inventory


class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_variant(self, product_variant_id):
        return self.db.query(Inventory).filter(Inventory.product_variant_id == product_variant_id).first()

    def get_for_variant_locked(self, product_variant_id):
        return (
            self.db.query(Inventory)
            .filter(Inventory.product_variant_id == product_variant_id)
            .with_for_update()
            .first()
        )
