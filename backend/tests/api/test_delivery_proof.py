"""Phase 6: one-time expiring pickup/handover codes, package count, idempotent event log."""
import re
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.timezone import utcnow
from app.main import app
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_proof import DeliveryCode, DeliveryEvent
from app.models.order import Order


@pytest.fixture()
def run(db, make_user):
    buyer = make_user()
    seller = make_user(role="tailor")
    rider = make_user(role="delivery_partner")
    other_rider = make_user(role="delivery_partner")
    admin = make_user(role="admin")
    partner = DeliveryPartner(user_id=rider.id, vehicle_type="bike", is_verified=True, is_available=False)
    db.add_all([partner, DeliveryPartner(user_id=other_rider.id, vehicle_type="bike", is_verified=True)])
    order = Order(order_number="PR-" + uuid.uuid4().hex[:10].upper(), order_type="customer_order",
                  buyer_user_id=buyer.id, seller_user_id=seller.id, status="ready_for_delivery",
                  subtotal=50000, total_amount=50000, currency="NGN", ordered_at=utcnow())
    db.add(order)
    db.flush()
    delivery = Delivery(order_id=order.id, delivery_request_id=uuid.uuid4(), status="assigned",
                        provider="internal", delivery_fee=2500, delivery_partner_id=partner.id)
    db.add(delivery)
    db.commit()
    current = [seller]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield {"http": http, "current": current, "db": db, "order": order, "delivery": delivery,
               "buyer": buyer, "seller": seller, "rider": rider, "other_rider": other_rider, "admin": admin,
               "base": f"/api/v1/deliveries/{delivery.id}"}
    app.dependency_overrides.clear()


def _as(run, who):
    run["current"][0] = run[who]
    return run["http"]


def _wrong(code):
    return "000000" if code != "000000" else "111111"


def _pick_up(run, **body):
    code = _as(run, "seller").get(run["base"] + "/pickup-code").json()["pickup_code"]
    return _as(run, "rider").post(run["base"] + "/picked-up", json={"pickup_code": code, **body})


def test_only_the_seller_sees_the_pickup_code_and_the_rider_must_enter_it(run):
    base, db = run["base"], run["db"]
    for who in ("rider", "buyer", "other_rider"):
        assert _as(run, who).get(base + "/pickup-code").status_code == 404, who
    issued = _as(run, "seller").get(base + "/pickup-code").json()
    assert issued["required"] is True and re.fullmatch(r"\d{6}", issued["pickup_code"]) and issued["expires_at"]
    # Stable while valid, and never stored in plaintext.
    assert _as(run, "seller").get(base + "/pickup-code").json()["pickup_code"] == issued["pickup_code"]
    stored = db.query(DeliveryCode).filter_by(purpose="pickup").one()
    assert issued["pickup_code"] not in str(stored.__dict__)

    http = _as(run, "rider")
    assert http.post(base + "/picked-up", json={"pickup_code": _wrong(issued["pickup_code"])}).status_code == 422
    assert db.get(Delivery, run["delivery"].id).status == "assigned"
    done = http.post(base + "/picked-up", json={"pickup_code": issued["pickup_code"], "package_count": 3})
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "in_transit" and done.json()["package_count"] == 3
    db.expire_all()
    assert db.query(DeliveryCode).filter_by(purpose="pickup").one().used_at is not None
    # Once collected, the seller's code is gone.
    assert _as(run, "seller").get(base + "/pickup-code").status_code == 409


def test_handover_code_is_stable_until_rotated_or_expired_and_burns_on_use(run):
    base, db = run["base"], run["db"]
    assert _pick_up(run).status_code == 200
    assert _as(run, "rider").get(base + "/handover-code").status_code == 404
    first = _as(run, "buyer").get(base + "/handover-code").json()
    assert re.fullmatch(r"\d{6}", first["handover_code"]) and first["expires_at"] and first["package_count"] == 1
    assert _as(run, "buyer").get(base + "/handover-code").json()["handover_code"] == first["handover_code"]

    # Rotation: the old code stops working at once.
    rotated = _as(run, "buyer").post(base + "/handover-code/rotate").json()
    old_still_valid = rotated["handover_code"] == first["handover_code"]  # 1-in-a-million collision
    if not old_still_valid:
        assert _as(run, "rider").post(base + "/delivered", json={"handover_code": first["handover_code"]}).status_code == 422

    # Expiry: a lapsed code is refused, and the buyer's next view issues a fresh one.
    live = db.query(DeliveryCode).filter_by(purpose="handover", used_at=None, revoked_at=None).one()
    live.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    expired = _as(run, "rider").post(base + "/delivered", json={"handover_code": rotated["handover_code"]})
    assert expired.status_code == 422 and "expired" in expired.text
    fresh = _as(run, "buyer").get(base + "/handover-code").json()
    done = _as(run, "rider").post(base + "/delivered", json={"handover_code": fresh["handover_code"]})
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "delivered"
    assert _as(run, "buyer").get(base + "/handover-code").status_code == 409


def test_retried_requests_with_the_same_idempotency_key_apply_once(run):
    base, db = run["base"], run["db"]
    headers = {"Idempotency-Key": "pickup-" + uuid.uuid4().hex}
    code = _as(run, "seller").get(base + "/pickup-code").json()["pickup_code"]
    http = _as(run, "rider")
    first = http.post(base + "/picked-up", json={"pickup_code": code, "package_count": 2}, headers=headers)
    retry = http.post(base + "/picked-up", json={"pickup_code": code, "package_count": 2}, headers=headers)
    assert first.status_code == retry.status_code == 200 and retry.json()["status"] == "in_transit"
    assert db.query(DeliveryEvent).filter_by(delivery_id=run["delivery"].id, event_type="picked_up").count() == 1
    # Without a key, a repeat is a plain state error; reusing a key for another action is refused.
    assert http.post(base + "/picked-up", json={"pickup_code": code}).status_code == 409
    assert http.post(base + "/delivered", json={"handover_code": "123456"}, headers=headers).status_code == 409
    assert http.post(base + "/delivered", json={"handover_code": "123456"},
                     headers={"Idempotency-Key": "bad key!"}).status_code == 422


def test_event_log_is_admin_only_and_never_contains_codes(run):
    base = run["base"]
    code = _as(run, "seller").get(base + "/pickup-code").json()["pickup_code"]
    _as(run, "rider").post(base + "/picked-up", json={"pickup_code": _wrong(code)})
    _as(run, "rider").post(base + "/picked-up", json={"pickup_code": code})
    handover = _as(run, "buyer").get(base + "/handover-code").json()["handover_code"]
    _as(run, "rider").post(base + "/delivered", json={"handover_code": handover})

    url = f"/api/v1/admin/dispatch/deliveries/{run['delivery'].id}/events"
    for who in ("buyer", "seller", "rider"):
        assert _as(run, who).get(url).status_code in {403, 404}, who
    response = _as(run, "admin").get(url)
    assert response.status_code == 200, response.text
    types = [e["event_type"] for e in response.json()]
    assert types == ["pickup_code_issued", "pickup_verification_failed", "picked_up",
                     "handover_code_issued", "delivered"]
    assert code not in response.text and handover not in response.text
    picked = next(e for e in response.json() if e["event_type"] == "picked_up")
    assert picked["actor_role"] == "delivery_partner" and picked["details"]["verified_by"] == "pickup_code"


def test_repeated_wrong_codes_lock_the_step(run):
    base = run["base"]
    code = _as(run, "seller").get(base + "/pickup-code").json()["pickup_code"]
    http = _as(run, "rider")
    statuses = [http.post(base + "/picked-up", json={"pickup_code": _wrong(code)}).status_code for _ in range(5)]
    assert statuses == [422] * 5
    assert http.post(base + "/picked-up", json={"pickup_code": code}).status_code == 403


def test_pickup_code_can_be_switched_off(run, monkeypatch):
    monkeypatch.setattr(settings, "DELIVERY_PICKUP_CODE_REQUIRED", False)
    base = run["base"]
    assert _as(run, "seller").get(base + "/pickup-code").json() == {
        "delivery_id": str(run["delivery"].id), "required": False, "pickup_code": None, "expires_at": None}
    done = _as(run, "rider").post(base + "/picked-up")
    assert done.status_code == 200 and done.json()["package_count"] == 1
