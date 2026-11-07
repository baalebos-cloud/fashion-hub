"""Logistics phase 4: multi-stop routes for one rider, built from separate deliveries."""
import uuid

import pytest
from fastapi.testclient import TestClient
from redis import Redis

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.timezone import utcnow
from app.main import app
from app.models.delivery import Delivery
from app.models.delivery_batch import DeliveryBatch
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.location import Location
from app.models.order import Order


@pytest.fixture(autouse=True)
def flags(monkeypatch):
    monkeypatch.setattr(settings, "ROUTING_PROVIDER", "none")
    monkeypatch.setattr(settings, "DISPATCH_MULTISTOP_ENABLED", True)
    monkeypatch.setattr(settings, "DELIVERY_PICKUP_CODE_REQUIRED", False)
    redis = Redis.from_url(settings.REDIS_URL)
    for key in redis.scan_iter("routing:*"):
        redis.delete(key)


@pytest.fixture()
def world(db, make_user):
    seller, buyer, admin = make_user(role="tailor"), make_user(), make_user(role="admin")
    rider_user = make_user(role="delivery_partner", full_name="Sola Bello")
    base = Location(location_type="rider_current", latitude=6.50, longitude=3.37)
    db.add(base)
    db.flush()
    rider = DeliveryPartner(user_id=rider_user.id, is_verified=True, is_available=True, vehicle_type="bike",
                            current_location_id=base.id)
    db.add(rider)
    db.commit()
    current = [admin]

    def job(lat_offset=0.0):
        pickup = Location(location_type="delivery_pickup", latitude=6.51 + lat_offset, longitude=3.37)
        dropoff = Location(location_type="delivery_dropoff", latitude=6.45 + lat_offset, longitude=3.47)
        order = Order(order_number="MS-" + uuid.uuid4().hex[:10].upper(), order_type="customer_order",
                      buyer_user_id=buyer.id, seller_user_id=seller.id, status="ready_for_delivery",
                      subtotal=20000, total_amount=20000, currency="NGN", ordered_at=utcnow())
        db.add_all([pickup, dropoff, order])
        db.flush()
        req = DeliveryRequest(order_id=order.id, pickup_location_id=pickup.id, dropoff_location_id=dropoff.id,
                              status="requested", proposed_fee=2000)
        db.add(req)
        db.commit()
        return req

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        def assign(req):
            current[0] = admin
            return http.post(f"/api/v1/admin/dispatch/requests/{req.id}/assign",
                             json={"partner_id": str(rider.id), "reason": "Batching nearby jobs"})
        yield {"http": http, "current": current, "rider": rider, "rider_user": rider_user, "admin": admin,
               "job": job, "assign": assign, "db": db}
    app.dependency_overrides.clear()


def test_dispatcher_builds_a_feasible_route_and_capacity_is_enforced(world):
    db = world["db"]
    first, second, third, fourth = world["job"](), world["job"](0.01), world["job"](0.02), world["job"](0.03)
    assert world["assign"](first).status_code == 200
    assert world["assign"](second).status_code == 200, "busy rider can take a second job when the route fits"
    batch = db.query(DeliveryBatch).filter_by(delivery_partner_id=world["rider"].id, status="active").one()
    assert len(batch.stops) == 4 and batch.total_minutes > 0 and batch.matrix_source == "straight_line_estimate"
    seen = set()
    for stop in batch.stops:  # pickup before drop-off, every time
        if stop["kind"] == "pickup":
            seen.add(stop["job"])
        else:
            assert stop["job"] in seen
    assert world["assign"](third).status_code == 200  # bike carries 3
    refused = world["assign"](fourth)
    assert refused.status_code == 409 and "carry" in refused.text
    # Each order still has its own delivery record.
    assert db.query(Delivery).filter_by(delivery_partner_id=world["rider"].id).count() == 3


def test_route_follows_pickups_and_deliveries_and_closes_when_done(world):
    db, http, current = world["db"], world["http"], world["current"]
    a, b = world["job"](), world["job"](0.01)
    da = world["assign"](a).json()["delivery_id"]
    world["assign"](b)
    current[0] = world["rider_user"]
    route = http.get("/api/v1/deliveries/mine/route").json()
    assert route and len(route["stops"]) == 4 and route["estimated"] is True
    assert http.post(f"/api/v1/deliveries/{da}/picked-up").status_code == 200
    route = http.get("/api/v1/deliveries/mine/route").json()
    assert len(route["stops"]) == 3  # a's pickup is done; its drop-off is still on the route
    from app.services.delivery_handover import DeliveryCodeService
    delivery_a = db.get(Delivery, uuid.UUID(da))
    code = DeliveryCodeService(db).reveal(delivery=delivery_a, purpose="handover", actor=world["admin"])["code"]
    db.commit()
    assert http.post(f"/api/v1/deliveries/{da}/delivered", json={"handover_code": code}).status_code == 200
    assert http.get("/api/v1/deliveries/mine/route").json() is None  # one delivery left: nothing to sequence
    current[0] = world["admin"]
    assert http.get(f"/api/v1/admin/dispatch/riders/{world['rider'].id}/route").json() is None


def test_turning_multistop_off_keeps_single_job_dispatch(world, monkeypatch):
    monkeypatch.setattr(settings, "DISPATCH_MULTISTOP_ENABLED", False)
    assert world["assign"](world["job"]()).status_code == 200
    refused = world["assign"](world["job"](0.01))
    assert refused.status_code == 409 and "not on another delivery" in refused.text
    assert world["db"].query(DeliveryBatch).count() == 0
