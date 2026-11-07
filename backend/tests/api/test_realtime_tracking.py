"""Logistics phase 2: rider tracking freshness, replay protection, device state, clean-up."""
import logging
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from redis import Redis

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.timezone import utcnow
from app.main import app
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.location import Location
from app.models.order import Order
from app.services import delivery_position
from app.services.delivery_position import freshness

DROP = (6.4474, 3.4728)


@pytest.fixture()
def run(db, make_user):
    buyer, seller, rider, admin, stranger = (make_user(), make_user(role="tailor"), make_user(role="delivery_partner"),
                                             make_user(role="admin"), make_user())
    partner = DeliveryPartner(user_id=rider.id, is_verified=True, is_available=False, vehicle_type="bike")
    pickup = Location(location_type="delivery_pickup", latitude=6.51, longitude=3.37)
    dropoff = Location(location_type="delivery_dropoff", latitude=DROP[0], longitude=DROP[1])
    order = Order(order_number="RT-" + uuid.uuid4().hex[:10].upper(), order_type="customer_order",
                  buyer_user_id=buyer.id, seller_user_id=seller.id, status="out_for_delivery",
                  subtotal=40000, total_amount=40000, currency="NGN", ordered_at=utcnow())
    db.add_all([partner, pickup, dropoff, order])
    db.flush()
    req = DeliveryRequest(order_id=order.id, pickup_location_id=pickup.id, dropoff_location_id=dropoff.id, status="assigned")
    db.add(req)
    db.flush()
    delivery = Delivery(order_id=order.id, delivery_request_id=req.id, status="in_transit", provider="internal",
                        delivery_fee=2000, delivery_partner_id=partner.id)
    db.add(delivery)
    db.commit()
    current = [rider]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        base = f"/api/v1/deliveries/{delivery.id}/position"
        token = http.post(base + "/start").json()["share_token"]
        yield {"http": http, "current": current, "base": base, "token": token, "delivery": delivery, "order": order,
               "db": db, "buyer": buyer, "rider": rider, "admin": admin, "stranger": stranger}
    app.dependency_overrides.clear()
    delivery_position.clear_position(delivery.id)


def _send(run, *, seconds_ago=None, fix=None, lat=6.48, lng=3.42):
    run["current"][0] = run["rider"]
    fix = fix or (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()
    return run["http"].post(run["base"], json={"latitude": lat, "longitude": lng, "accuracy_m": 12,
                                                "share_token": run["token"], "recorded_at": fix})


def test_replayed_out_of_order_stale_and_future_points_are_refused(run):
    first = (datetime.now(timezone.utc) - timedelta(seconds=20)).isoformat()
    assert _send(run, fix=first).json()["accepted"] is True
    assert _send(run, fix=first).status_code == 422               # the identical point again (replay)
    assert _send(run, seconds_ago=40).status_code == 422          # older than the last one
    assert _send(run, seconds_ago=19).json()["accepted"] is False  # 1 s later: ignored, not an error
    assert _send(run, seconds_ago=500).status_code == 422         # too old to share
    assert _send(run, seconds_ago=-120).status_code == 422        # phone clock far in the future
    assert _send(run, seconds_ago=5).json()["accepted"] is True


def test_customers_see_freshness_and_a_last_known_point_is_never_shown_as_current(run):
    _send(run, seconds_ago=10)
    run["current"][0] = run["buyer"]
    seen = run["http"].get(run["base"]).json()
    assert seen["freshness"] == "live" and seen["age_seconds"] >= 10
    now = datetime.now(timezone.utc)
    stamp = lambda s: {"recorded_at": (now - timedelta(seconds=s)).isoformat()}  # noqa: E731
    assert freshness(stamp(29), now)[0] == "live" and freshness(stamp(60), now)[0] == "delayed"
    assert freshness(stamp(300), now)[0] == "last_known" and freshness(stamp(900), now)[0] == "unavailable"


def test_sharing_stays_alive_while_the_rider_keeps_sending(run):
    redis = Redis.from_url(settings.REDIS_URL)
    key = f"delivery:gps:{run['delivery'].id}:consent"
    redis.expire(key, 60)  # nearly lapsed
    _send(run, seconds_ago=5)
    assert redis.ttl(key) > 3000


def test_phone_can_say_location_is_off_and_everyone_sees_why_without_coordinates(run):
    run["current"][0] = run["rider"]
    assert run["http"].post(run["base"] + "/state", json={"share_token": run["token"],
                                                          "state": "permission_denied"}).status_code == 204
    run["current"][0] = run["buyer"]
    journey = run["http"].get(f"/api/v1/deliveries/orders/{run['order'].id}/journey").json()
    assert journey["tracking"]["state"] == "permission_denied" and journey["live"] is None
    run["current"][0] = run["admin"]
    board = run["http"].get("/api/v1/admin/dispatch-board").json()
    mine = next(r for r in board["active"] if r["id"] == str(run["delivery"].id))
    assert mine["tracking"]["state"] == "permission_denied"
    # A new point clears the "off" state.
    _send(run, seconds_ago=5)
    run["current"][0] = run["buyer"]
    assert run["http"].get(f"/api/v1/deliveries/orders/{run['order'].id}/journey").json()["tracking"]["state"] == "live"
    assert run["http"].post(run["base"] + "/state", json={"share_token": "x" * 40, "state": "paused"}).status_code == 403


def test_only_parties_can_read_the_position_and_logs_hold_no_coordinates(run):
    import io
    captured = io.StringIO()
    handler = logging.StreamHandler(captured)
    handler.setLevel(logging.DEBUG)
    root = logging.getLogger()
    root.addHandler(handler)
    previous = root.level
    root.setLevel(logging.DEBUG)
    try:
        _send(run, seconds_ago=5, lat=6.4812345, lng=3.4212345)
        run["current"][0] = run["stranger"]
        assert run["http"].get(run["base"]).status_code == 404
    finally:
        root.removeHandler(handler)
        root.setLevel(previous)
    assert "6.4812345" not in captured.getvalue() and "3.4212345" not in captured.getvalue()


def test_tracking_ends_when_the_package_is_handed_over(run, monkeypatch):
    _send(run, seconds_ago=5)
    monkeypatch.setattr(settings, "DELIVERY_PICKUP_CODE_REQUIRED", False)
    db = run["db"]
    from app.services.delivery_handover import DeliveryCodeService
    code = DeliveryCodeService(db).reveal(delivery=run["delivery"], purpose="handover", actor=run["buyer"])["code"]
    db.commit()
    run["current"][0] = run["rider"]
    done = run["http"].post(f"/api/v1/deliveries/{run['delivery'].id}/delivered", json={"handover_code": code})
    assert done.status_code == 200, done.text
    assert delivery_position.read_position(run["delivery"].id) is None
    assert delivery_position.tracking_status(run["delivery"].id)["sharing"] is False
