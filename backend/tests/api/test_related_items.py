"""Recommendations PR 2: learned related items, fallbacks and the public endpoints."""
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.timezone import utcnow
from app.main import app
from app.models.interaction_event import InteractionEvent
from app.models.inventory import Inventory
from app.models.item_similarity import ItemSimilarity
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.models.vendor import Vendor
from app.models.vendor_product import VendorProduct
from app.services import similarity_service
from app.services.cart_service import CartService

CATEGORY = uuid.uuid4()


@pytest.fixture()
def client(db):
    limiter.reset()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as http:
        yield http
    app.dependency_overrides.clear()


@pytest.fixture()
def shop(db):
    """A verified vendor; shop.product(...) adds an in-stock product."""
    owner = User(email=uuid.uuid4().hex + "@example.com", full_name="Vendor", role="vendor", hashed_password="x")
    db.add(owner)
    db.flush()
    vendor = Vendor(user_id=owner.id, business_name="Lagos Fabrics", is_verified=True)
    db.add(vendor)
    db.flush()

    class Shop:
        def product(self, name, price="1000", *, stock=5, category=CATEGORY, active=True, owner_vendor=vendor):
            product = VendorProduct(vendor_id=owner_vendor.id, name=name, base_price=Decimal(price),
                                    category_id=category, is_active=active)
            db.add(product)
            db.flush()
            variant = ProductVariant(product_id=product.id, sku="S-" + uuid.uuid4().hex, price=Decimal(price))
            db.add(variant)
            db.flush()
            db.add(Inventory(product_variant_id=variant.id, quantity_available=stock, quantity_reserved=0))
            db.commit()
            return product

    return Shop()


def _activity(db, shopper, event, *products, days_ago=0):
    for product in products:
        db.add(InteractionEvent(anonymous_id=shopper, event_type=event, item_type="product", item_id=product.id,
                                occurred_at=utcnow() - timedelta(days=days_ago)))
    db.commit()


def _shoppers(n):
    return [str(uuid.uuid4()) for _ in range(n)]


def test_items_engaged_with_by_the_same_shoppers_become_related(db, shop):
    lace, gele, ankara = shop.product("Lace"), shop.product("Gele"), shop.product("Ankara")
    for shopper in _shoppers(3):
        _activity(db, shopper, "view", lace, gele)
    _activity(db, str(uuid.uuid4()), "view", lace, ankara)  # only one shopper: not enough

    result = similarity_service.rebuild(db)
    assert result["pairs"] == 2  # lace->gele and gele->lace
    (row,) = db.query(ItemSimilarity).filter_by(item_id=lace.id, signal="viewed_together").all()
    assert row.related_id == gele.id and row.support == 3 and 0 < row.score <= 1


def test_bought_together_only_counts_cart_adds_and_purchases(db, shop):
    lace, gele, thread = shop.product("Lace"), shop.product("Gele"), shop.product("Thread")
    for shopper in _shoppers(2):
        _activity(db, shopper, "purchase", lace, thread)
        _activity(db, shopper, "view", lace, gele)
    similarity_service.rebuild(db)
    bought = {r.related_id for r in db.query(ItemSimilarity).filter_by(item_id=lace.id, signal="bought_together")}
    viewed = {r.related_id for r in db.query(ItemSimilarity).filter_by(item_id=lace.id, signal="viewed_together")}
    assert bought == {thread.id}
    assert viewed == {thread.id, gele.id}


def test_rebuild_replaces_the_previous_set(db, shop):
    lace, gele = shop.product("Lace"), shop.product("Gele")
    for shopper in _shoppers(2):
        _activity(db, shopper, "view", lace, gele)
    similarity_service.rebuild(db)
    db.query(InteractionEvent).delete()
    db.commit()
    assert similarity_service.rebuild(db)["pairs"] == 0
    assert db.query(ItemSimilarity).count() == 0


def test_product_page_shows_learned_items_then_labelled_fallbacks(db, shop, client):
    lace = shop.product("Lace", "1000")
    gele = shop.product("Gele", "5000", category=uuid.uuid4())  # learned, so category doesn't matter
    close = shop.product("Close price", "1100")
    far = shop.product("Far price", "1400")
    shop.product("Out of band", "9000")
    for shopper in _shoppers(2):
        _activity(db, shopper, "view", lace, gele)
    similarity_service.rebuild(db)

    response = client.get(f"/api/v1/recommendations/products/{lace.id}/similar", params={"limit": 3})
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [(i["name"], i["reason"], i["learned"]) for i in items] == [
        ("Gele", "viewed_together", True), ("Close price", "similar", False), ("Far price", "similar", False)]
    assert items[0]["vendor_name"] == "Lagos Fabrics" and items[0]["price_ngn"] == 5000.0


def test_suggestions_exclude_items_nobody_can_buy(db, shop, client):
    lace = shop.product("Lace")
    sold_out = shop.product("Sold out", stock=0)
    hidden = shop.product("Hidden", active=False)
    for shopper in _shoppers(2):
        _activity(db, shopper, "view", lace, sold_out, hidden)
    similarity_service.rebuild(db)
    names = [i["name"] for i in client.get(f"/api/v1/recommendations/products/{lace.id}/similar").json()["items"]]
    assert "Sold out" not in names and "Hidden" not in names and "Lace" not in names


def test_same_vendor_fallback_when_nothing_in_the_category(db, shop, client):
    lace = shop.product("Lace", category=None)
    shop.product("Other from this shop", "800", category=uuid.uuid4())
    items = client.get(f"/api/v1/recommendations/products/{lace.id}/similar").json()["items"]
    assert [(i["name"], i["reason"]) for i in items] == [("Other from this shop", "same_vendor")]


def test_cart_shows_often_bought_together_excluding_cart_items(db, shop, client):
    lace, gele, thread, lining = (shop.product(n) for n in ("Lace", "Gele", "Thread", "Lining"))
    for shopper in _shoppers(2):
        _activity(db, shopper, "add_to_cart", lace, gele, thread)
    for shopper in _shoppers(2):
        _activity(db, shopper, "view", lace, lining)  # viewed, never bought together
    similarity_service.rebuild(db)
    response = client.get("/api/v1/recommendations/products/bought-together",
                          params=[("product_id", str(lace.id)), ("product_id", str(gele.id))])
    items = response.json()["items"]
    assert items[0]["name"] == "Thread" and items[0]["reason"] == "bought_together" and items[0]["learned"]
    assert {i["name"] for i in items}.isdisjoint({"Lace", "Gele"})
    assert all(not i["learned"] for i in items if i["name"] == "Lining")


def test_unknown_product_is_404(client):
    assert client.get(f"/api/v1/recommendations/products/{uuid.uuid4()}/similar").status_code == 404


def test_cart_summary_includes_product_ids(db, shop, make_user):
    tailor = make_user(role="tailor")
    lace = shop.product("Lace")
    variant = db.query(ProductVariant).filter_by(product_id=lace.id).one()
    CartService(db).add_item(owner_user_id=tailor.id, product_variant_id=variant.id, quantity=1)
    summary = CartService(db).get_cart_summary(tailor.id)
    assert summary["items"][0]["product_id"] == lace.id
