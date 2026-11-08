"""A vendor can list a product in several colours, each with its own price and stock."""
import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.inventory_restock import InventoryRestock
from app.models.vendor import Vendor

IMG = ["/api/v1/media/files/lace.jpg"]


@pytest.fixture()
def ctx(db, make_user):
    vendor = make_user(role="vendor")
    db.add(Vendor(user_id=vendor.id, business_name="Lagos Fabrics", is_verified=True))
    db.commit()
    current = [vendor]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield dict(http=http, db=db, current=current)
    app.dependency_overrides.clear()


def _create(http, **extra):
    body = dict(name="French lace", base_price="9500.00", image_urls=IMG, unit_of_measure="yard", **extra)
    return http.post("/api/v1/vendor-products", json=body)


def test_one_version_per_colour_with_its_own_price_and_stock(ctx):
    res = _create(ctx["http"], colours=[dict(name="Royal blue", price="9500.00", stock=30),
                                         dict(name="Gold", price="10200.00", stock=12),
                                         dict(name="Navy", price="9000.00", stock=0)])
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["base_price"] == 9000.0  # lowest colour price
    by_colour = {v["attributes"]["color"]: v for v in body["variants"]}
    assert set(by_colour) == {"Royal blue", "Gold", "Navy"}
    assert by_colour["Gold"]["price"] == 10200.0 and by_colour["Gold"]["quantity_available"] == 12
    assert by_colour["Navy"]["quantity_available"] == 0
    # Starting stock is recorded once per colour that has any.
    assert ctx["db"].query(InventoryRestock).count() == 2
    stock = ctx["http"].get("/api/v1/vendor-inventory", params={"page_size": 100}).json()
    assert {row["colour"] for row in stock} == {"Royal blue", "Gold", "Navy"}


def test_without_colours_it_works_as_before(ctx):
    res = _create(ctx["http"], initial_stock=5)
    assert res.status_code == 201, res.text
    [variant] = res.json()["variants"]
    assert variant["attributes"] is None and variant["quantity_available"] == 5 and variant["price"] == 9500.0


@pytest.mark.parametrize("extra", [
    dict(colours=[dict(name="Gold", price="1.00", stock=1), dict(name="gold", price="2.00", stock=1)]),  # same name
    dict(colours=[dict(name="Gold", price="1.00", stock=1)], initial_stock=4),  # stock set twice
    dict(colours=[dict(name="Gold", price="0", stock=1)]),  # free
    dict(colours=[dict(name="Gold", price="1.00", stock=-1)]),
    dict(colours=[dict(name="", price="1.00", stock=1)]),
    dict(colours=[]),
    dict(colours=[dict(name=f"C{i}", price="1.00", stock=1) for i in range(21)]),
])
def test_rejects_unclear_colour_lists(ctx, extra):
    assert _create(ctx["http"], **extra).status_code == 422
