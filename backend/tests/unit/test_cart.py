"""Unit tests for CartService, focused on the "vendor sells out" edge case
at add-to-cart time (soft check) vs. checkout time (hard, atomic check --
see test_orders.py-style integration coverage in test_delivery.py's sibling
test_checkout flow for the authoritative enforcement)."""
import pytest

from app.core.exceptions import ConflictError
from app.models.inventory import Inventory
from app.models.product_variant import ProductVariant
from app.services.cart_service import CartService


def test_add_item_respects_available_stock(db, make_user):
    from app.core.constants import UserRole

    tailor = make_user(role=UserRole.TAILOR.value)
    variant = ProductVariant(product_id=tailor.id, sku="SKU-1", price=10.0)
    db.add(variant)
    db.flush()
    db.add(Inventory(product_variant_id=variant.id, quantity_available=2))
    db.commit()

    service = CartService(db)
    service.add_item(owner_user_id=tailor.id, product_variant_id=variant.id, quantity=2)

    with pytest.raises(ConflictError):
        service.add_item(owner_user_id=tailor.id, product_variant_id=variant.id, quantity=5)
