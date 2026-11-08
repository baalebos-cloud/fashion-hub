"""The tailor sees the customer's measurements for an order, and only while it's active."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.measurement import Measurement
from app.models.order import Order
from app.services.order_service import OrderService
from tests.catalog_helpers import catalog_request


@pytest.fixture()
def setup(db, make_user):
    customer, tailor = make_user(), make_user(role="tailor")
    order = OrderService(db).create_customer_order(**catalog_request(db, customer, tailor))
    current = [customer]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as client:
        yield dict(db=db, client=client, order=order, customer=customer, tailor=tailor, current=current, make_user=make_user)
    app.dependency_overrides.clear()


def _get(s, who):
    s["current"][0] = who
    return s["client"].get(f"/api/v1/orders/{s['order'].id}/measurements")


def _set_status(s, status):
    s["order"].status = status
    s["db"].commit()


def test_buyer_always_sees_their_own(setup):
    res = _get(setup, setup["customer"])
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["label"] == "My measurements"
    assert body["fields"] == [{"field_name": "chest", "value": "92.50", "unit": "cm"}]


@pytest.mark.parametrize("status", ["paid", "accepted", "in_production", "ready_for_delivery", "shipped", "out_for_delivery", "delivered"])
def test_tailor_sees_them_while_the_order_is_active(setup, status):
    _set_status(setup, status)
    res = _get(setup, setup["tailor"])
    assert res.status_code == 200, res.text
    assert res.json()["fields"][0]["field_name"] == "chest"


@pytest.mark.parametrize("status", ["pending", "received", "completed", "cancelled", "rejected", "refunded"])
def test_tailor_cannot_see_them_before_payment_or_after_close(setup, status):
    _set_status(setup, status)
    assert _get(setup, setup["tailor"]).status_code == 403
    assert _get(setup, setup["customer"]).status_code == 200


def test_other_users_and_admins_are_refused(setup):
    _set_status(setup, "in_production")
    assert _get(setup, setup["make_user"](role="tailor")).status_code == 403
    assert _get(setup, setup["make_user"]()).status_code == 403
    assert _get(setup, setup["make_user"](role="admin")).status_code == 403


def test_order_copy_is_fixed_when_the_profile_changes_later(setup):
    _set_status(setup, "accepted")
    db = setup["db"]
    field = db.query(Measurement).filter(Measurement.measurement_profile_id == setup["order"].measurement_profile_id).one()
    field.value = 120
    db.commit()
    assert _get(setup, setup["tailor"]).json()["fields"][0]["value"] == "92.50"


def test_missing_snapshot_and_unknown_order_are_not_found(setup):
    db = setup["db"]
    order = db.get(Order, setup["order"].id)
    order.measurement_snapshot = None
    order.status = "accepted"
    db.commit()
    assert _get(setup, setup["tailor"]).status_code == 404
    setup["current"][0] = setup["tailor"]
    assert setup["client"].get(f"/api/v1/orders/{uuid.uuid4()}/measurements").status_code == 404
