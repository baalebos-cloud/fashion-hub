"""Vendors choose when a stock line counts as low."""
import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.vendor import Vendor


@pytest.fixture()
def ctx(db, make_user):
    vendor = make_user(role="vendor")
    db.add(Vendor(user_id=vendor.id, business_name="Lagos Fabrics"))
    db.commit()
    current = [vendor]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield dict(http=http, current=current, make_user=make_user)
    app.dependency_overrides.clear()


def test_defaults_to_ten_and_can_be_changed(ctx):
    http = ctx["http"]
    assert http.get("/api/v1/vendors/me").json()["low_stock_threshold"] == 10
    res = http.patch("/api/v1/vendors/me/stock-alert", json={"low_stock_threshold": 25})
    assert res.status_code == 200, res.text
    assert res.json()["low_stock_threshold"] == 25
    assert http.get("/api/v1/vendors/me").json()["low_stock_threshold"] == 25
    assert http.patch("/api/v1/vendors/me/stock-alert", json={"low_stock_threshold": 0}).json()["low_stock_threshold"] == 0


@pytest.mark.parametrize("value", [-1, 1_000_001, "lots", None])
def test_rejects_out_of_range_values(ctx, value):
    assert ctx["http"].patch("/api/v1/vendors/me/stock-alert", json={"low_stock_threshold": value}).status_code == 422


def test_only_vendors_with_a_profile(ctx):
    http = ctx["http"]
    ctx["current"][0] = ctx["make_user"](role="vendor")
    assert http.patch("/api/v1/vendors/me/stock-alert", json={"low_stock_threshold": 5}).status_code == 404
    ctx["current"][0] = ctx["make_user"](role="tailor")
    assert http.patch("/api/v1/vendors/me/stock-alert", json={"low_stock_threshold": 5}).status_code == 403
