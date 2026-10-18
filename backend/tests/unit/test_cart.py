import pytest
from app.core.exceptions import ConflictError, NotFoundError, ForbiddenError
from app.services.cart_service import CartService
from tests.vendor_helpers import catalog


def test_add_item_respects_available_stock(db, make_user):
    tailor = make_user(role='tailor')
    _, vendor, _, variant, inventory = catalog(db, stock=2)
    service = CartService(db)
    item = service.add_item(owner_user_id=tailor.id, product_variant_id=variant.id, quantity=2)
    assert item.vendor_id == vendor.id
    assert inventory.quantity_reserved == 0
    with pytest.raises(ConflictError):
        service.add_item(owner_user_id=tailor.id, product_variant_id=variant.id, quantity=1)


def test_cart_mutations_require_owner_and_professional_role(db, make_user):
    owner, other = make_user(role='designer'), make_user(role='tailor')
    _, _, _, variant, _ = catalog(db)
    service = CartService(db)
    item = service.add_item(owner_user_id=owner.id, product_variant_id=variant.id, quantity=1)
    with pytest.raises(NotFoundError):
        service.update_quantity(owner_user_id=other.id, cart_item_id=item.id, quantity=2)
    with pytest.raises(NotFoundError):
        service.remove_item(item.id, owner_user_id=other.id)
    with pytest.raises(ForbiddenError):
        service.get_cart_summary(make_user().id)
    assert service.get_cart_summary(owner.id)['items'][0]['quantity'] == 1
