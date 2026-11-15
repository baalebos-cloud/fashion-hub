"""Customers can buy fabrics and accessories from verified vendors, like tailors."""
import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import create_access_token
from app.main import app
from app.models.order import Order
from tests.vendor_helpers import address, catalog


@pytest.fixture()
def client(db):
    def override_db():
        yield db
    app.dependency_overrides[get_db] = override_db
    limiter.reset()
    with TestClient(app) as http:
        yield http
    app.dependency_overrides.clear()


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(str(user.id), user.role)}


@pytest.mark.parametrize("role", ["customer", "tailor", "designer"])
def test_buyers_can_add_materials_and_check_out(client, db, make_user, role):
    buyer = make_user(role=role)
    _, vendor, _, variant, _ = catalog(db)
    home = address(db, buyer)
    added = client.post("/api/v1/carts/items", json={"product_variant_id": str(variant.id), "quantity": 2}, headers=auth(buyer))
    assert added.status_code == 201, added.text
    cart = added.json()
    key = "material-checkout-" + role
    r = client.post("/api/v1/checkout", headers={**auth(buyer), "Idempotency-Key": key}, json={
        "vendor_id": str(vendor.id), "cart_id": cart["cart_id"], "cart_revision": cart["revision"],
        "delivery_address_id": str(home.id), "idempotency_key": key})
    assert r.status_code == 201, r.text
    order = db.get(Order, r.json()["id"])
    assert order.order_type == "vendor_order" and str(order.buyer_user_id) == str(buyer.id)
    assert order.delivery_address_snapshot["city"]  # delivered to the buyer's own address


@pytest.mark.parametrize("role", ["vendor", "delivery_partner"])
def test_sellers_and_riders_have_no_material_cart(client, db, make_user, role):
    who = make_user(role=role)
    _, _, _, variant, _ = catalog(db)
    r = client.post("/api/v1/carts/items", json={"product_variant_id": str(variant.id), "quantity": 1}, headers=auth(who))
    assert r.status_code == 403
