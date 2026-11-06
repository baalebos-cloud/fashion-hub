"""Logistics phase 3: explainable rider scoring, dispatcher suggestions and manual assignment."""
import uuid

import pytest
from fastapi.testclient import TestClient
from redis import Redis

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.timezone import utcnow
from app.main import app
from app.models.audit_log import AuditLog
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.dispatch_job_offer import DispatchJobOffer
from app.models.location import Location
from app.models.order import Order
from app.services.auto_dispatch_service import AutoDispatchService
from app.services.dispatch_scoring import SCORING_VERSION

PICKUP = (6.5095, 3.3711)


@pytest.fixture(autouse=True)
def no_routing(monkeypatch):
    monkeypatch.setattr(settings, "ROUTING_PROVIDER", "none")
    redis = Redis.from_url(settings.REDIS_URL)
    for key in redis.scan_iter("routing:*"):
        redis.delete(key)


@pytest.fixture()
def world(db, make_user):
    seller, buyer, admin = make_user(role="tailor"), make_user(), make_user(role="admin")

    def rider(name, lat_offset, rating=0.0, **extra):
        user = make_user(role="delivery_partner", full_name=name)
        here = Location(location_type="rider_current", latitude=PICKUP[0] + lat_offset, longitude=PICKUP[1])
        db.add(here)
        db.flush()
        fields = {"is_verified": True, "is_available": True, "vehicle_type": "bike", **extra}
        partner = DeliveryPartner(user_id=user.id, current_location_id=here.id, average_rating=rating, **fields)
        db.add(partner)
        db.flush()
        return partner

    def job():
        pickup = Location(location_type="delivery_pickup", latitude=PICKUP[0], longitude=PICKUP[1])
        dropoff = Location(location_type="delivery_dropoff", latitude=6.4474, longitude=3.4728)
        order = Order(order_number="SD-" + uuid.uuid4().hex[:10].upper(), order_type="customer_order",
                      buyer_user_id=buyer.id, seller_user_id=seller.id, status="ready_for_delivery",
                      subtotal=30000, total_amount=30000, currency="NGN", ordered_at=utcnow())
        db.add_all([pickup, dropoff, order])
        db.flush()
        req = DeliveryRequest(order_id=order.id, pickup_location_id=pickup.id, dropoff_location_id=dropoff.id,
                              status="requested", proposed_fee=2500)
        db.add(req)
        db.commit()
        return req

    return {"rider": rider, "job": job, "admin": admin, "seller": seller, "buyer": buyer}


def test_scores_are_explained_reproducible_and_reward_nearness_reliability_and_fairness(world, db):
    near = world["rider"]("Near", 0.005, rating=4.0)
    far = world["rider"]("Far", 0.08, rating=4.0)
    flaky = world["rider"]("Flaky", 0.005, rating=4.0)
    busy_today = world["rider"]("Busy", 0.005, rating=4.0)
    job = world["job"]()
    for _ in range(6):  # Flaky ignored six automatic offers this month
        other = world["job"]()
        db.add(DispatchJobOffer(delivery_request_id=other.id, delivery_partner_id=flaky.id, status="expired",
                                attempt=1, expires_at=utcnow()))
    for _ in range(3):  # Busy already delivered three jobs today
        other = world["job"]()
        db.add(Delivery(order_id=other.order_id, delivery_request_id=other.id, status="delivered",
                        provider="internal", delivery_fee=1000, delivery_partner_id=busy_today.id))
    db.commit()
    service = AutoDispatchService(db)
    first = service.ranked_candidates(job, smart=True)
    again = service.ranked_candidates(job, smart=True)
    assert [p.id for p, _, _ in first] == [p.id for p, _, _ in again]  # reproducible
    order = [p.id for p, _, _ in first]
    assert order[0] == near.id and order.index(near.id) < order.index(far.id)
    assert order.index(near.id) < order.index(flaky.id) and order.index(near.id) < order.index(busy_today.id)
    record = first[0][2]
    assert record["version"] == SCORING_VERSION and 0 <= record["score"] <= 100
    assert set(record["factors"]) == {"pickup", "reliability", "rating", "experience", "fairness"}
    assert "pickup in about" in record["explanation"] and "(estimate)" in record["explanation"]


def test_ineligible_riders_never_appear(world, db):
    ok = world["rider"]("Ok", 0.01)
    world["rider"]("Offline", 0.01, is_available=False)
    unverified = world["rider"]("Unverified", 0.01)
    unverified.is_verified = False
    world["rider"]("TooFar", 0.5)  # ~55 km, outside the radius
    busy = world["rider"]("OnAJob", 0.01)
    other = world["job"]()
    db.add(Delivery(order_id=other.order_id, delivery_request_id=other.id, status="in_transit",
                    provider="internal", delivery_fee=1000, delivery_partner_id=busy.id))
    db.commit()
    ranked = AutoDispatchService(db).ranked_candidates(world["job"](), smart=True)
    assert [p.id for p, _, _ in ranked] == [ok.id]


def test_automatic_offer_records_why_the_rider_was_chosen(world, db, monkeypatch):
    monkeypatch.setattr(settings, "DISPATCH_AUTO_OFFER_ENABLED", True)
    monkeypatch.setattr(settings, "DISPATCH_SMART_SCORING_ENABLED", True)
    world["rider"]("Near", 0.005)
    job = world["job"]()
    offer = AutoDispatchService(db).offer_next(job.id)
    assert offer.score is not None and offer.score_details["version"] == SCORING_VERSION
    assert offer.score_details["explanation"]


def test_scoring_off_keeps_the_original_order(world, db):
    near, far = world["rider"]("Near", 0.005, rating=1.0), world["rider"]("Far", 0.08, rating=5.0)
    ranked = AutoDispatchService(db).ranked_candidates(world["job"]())
    assert [p.id for p, _, _ in ranked] == [near.id, far.id] and ranked[0][2] is None


@pytest.fixture()
def http(db, world):
    current = [world["admin"]]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as client:
        yield client, current
    app.dependency_overrides.clear()


def test_dispatcher_sees_suggestions_and_can_assign_once(world, db, http):
    client, current = http
    near, far = world["rider"]("Near", 0.005), world["rider"]("Far", 0.05)
    job = world["job"]()
    suggestions = client.get(f"/api/v1/admin/dispatch/requests/{job.id}/candidates").json()
    assert [s["first_name"] for s in suggestions] == ["Near", "Far"]
    assert suggestions[0]["explanation"] and suggestions[0]["score"] >= suggestions[1]["score"]

    body = {"partner_id": str(far.id), "reason": "Customer asked for this rider"}
    assigned = client.post(f"/api/v1/admin/dispatch/requests/{job.id}/assign", json=body)
    assert assigned.status_code == 200, assigned.text
    delivery = db.get(Delivery, uuid.UUID(assigned.json()["delivery_id"]))
    assert delivery.delivery_partner_id == far.id
    assert db.query(AuditLog).filter_by(action="dispatch.assigned_by_dispatcher").count() == 1
    # A second assignment for the same job is refused; so is a rider who is now busy.
    again = client.post(f"/api/v1/admin/dispatch/requests/{job.id}/assign",
                        json={"partner_id": str(near.id), "reason": "Second attempt"})
    assert again.status_code == 409
    other = world["job"]()
    busy = client.post(f"/api/v1/admin/dispatch/requests/{other.id}/assign",
                       json={"partner_id": str(far.id), "reason": "Rider already busy"})
    assert busy.status_code == 409
    assert client.post(f"/api/v1/admin/dispatch/requests/{other.id}/assign",
                       json={"partner_id": str(near.id), "reason": "x"}).status_code == 422  # reason required
    current[0] = world["seller"]
    assert client.get(f"/api/v1/admin/dispatch/requests/{other.id}/candidates").status_code == 403
