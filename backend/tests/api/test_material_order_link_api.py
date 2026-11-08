"""Material purchases carry the customer order they're for, and the tailor can link one over HTTP."""
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.timezone import utcnow
from app.main import app
from app.models.order import Order


def _order(prefix, kind, buyer, seller, status, **extra):
    return Order(order_number=prefix + uuid.uuid4().hex[:18], order_type=kind, buyer_user_id=buyer.id, seller_user_id=seller.id,
                 status=status, subtotal=Decimal(1000), total_amount=Decimal(1000), currency="NGN", ordered_at=utcnow(), **extra)


@pytest.fixture()
def ctx(db, make_user):
    tailor, customer, vendor = make_user(role="tailor"), make_user(), make_user(role="vendor")
    garment = _order("CO-", "customer_order", customer, tailor, "accepted")
    db.add(garment)
    db.flush()
    linked = _order("VO-", "vendor_order", tailor, vendor, "paid", parent_customer_order_id=garment.id)
    loose = _order("VO-", "vendor_order", tailor, vendor, "checkout")
    db.add_all([linked, loose])
    db.commit()
    current = [tailor]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield dict(http=http, current=current, tailor=tailor, vendor=vendor, customer=customer, garment=garment, linked=linked, loose=loose)
    app.dependency_overrides.clear()


def test_order_responses_include_the_parent_customer_order(ctx):
    http = ctx["http"]
    detail = http.get(f"/api/v1/orders/{ctx['linked'].id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["parent_customer_order_id"] == str(ctx["garment"].id)
    buying = http.get("/api/v1/orders", params={"perspective": "buying", "order_type": "vendor_order"}).json()
    by_id = {o["id"]: o for o in buying}
    assert by_id[str(ctx["linked"].id)]["parent_customer_order_id"] == str(ctx["garment"].id)
    assert by_id[str(ctx["loose"].id)]["parent_customer_order_id"] is None
    assert http.get(f"/api/v1/orders/{ctx['garment'].id}").json()["parent_customer_order_id"] is None


def test_vendor_sees_which_order_it_is_for(ctx):
    ctx["current"][0] = ctx["vendor"]
    assert ctx["http"].get(f"/api/v1/orders/{ctx['linked'].id}").json()["parent_customer_order_id"] == str(ctx["garment"].id)


def test_tailor_links_an_unpaid_material_order_and_cannot_relink_it(ctx):
    http = ctx["http"]
    url = f"/api/v1/orders/{ctx['garment'].id}/material-orders/{ctx['loose'].id}/link"
    res = http.post(url)
    assert res.status_code == 200, res.text
    assert res.json()["parent_customer_order_id"] == str(ctx["garment"].id)
    assert http.post(url).status_code == 200  # same link again is fine
    ctx["current"][0] = ctx["customer"]
    assert http.post(url).status_code == 403
