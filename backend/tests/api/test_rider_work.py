"""A rider's History, Earnings and dashboard show their own finished jobs."""
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import create_access_token
from app.core.timezone import utcnow
from app.main import app
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.location import Location
from app.models.order import Order


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


def job(db, partner, *, status, fee, delivered_ago=None, customer, tailor):
    order = Order(order_number="T-" + uuid.uuid4().hex[:10], order_type="customer_order", buyer_user_id=customer.id,
                  seller_user_id=tailor.id, status="delivered", subtotal=Decimal("100"), total_amount=Decimal("100"),
                  currency="NGN", ordered_at=utcnow())
    a = Location(location_type="delivery_pickup", latitude=6.5, longitude=3.37, formatted_address="a", country="NG")
    b = Location(location_type="delivery_dropoff", latitude=6.45, longitude=3.47, formatted_address="b", country="NG")
    db.add_all([order, a, b]); db.flush()
    req = DeliveryRequest(order_id=order.id, pickup_location_id=a.id, dropoff_location_id=b.id, status="assigned")
    db.add(req); db.flush()
    d = Delivery(order_id=order.id, delivery_request_id=req.id, status=status, provider="internal",
                 delivery_fee=Decimal(fee), delivery_partner_id=partner.id,
                 delivered_at=(utcnow() - delivered_ago) if delivered_ago is not None else None)
    db.add(d); db.commit()
    return d


@pytest.fixture()
def world(db, make_user):
    rider, other = make_user(role="delivery_partner"), make_user(role="delivery_partner")
    customer, tailor = make_user(role="customer"), make_user(role="tailor")
    mine = DeliveryPartner(user_id=rider.id, is_verified=True, is_available=True, average_rating=Decimal("4.8"))
    theirs = DeliveryPartner(user_id=other.id, is_verified=True, is_available=True)
    db.add_all([mine, theirs]); db.commit()
    kw = dict(customer=customer, tailor=tailor)
    jobs = {
        "today": job(db, mine, status="delivered", fee="2500", delivered_ago=timedelta(minutes=5), **kw),
        "old": job(db, mine, status="delivered", fee="4000", delivered_ago=timedelta(days=40), **kw),
        "active": job(db, mine, status="in_transit", fee="3000", **kw),
        "cancelled": job(db, mine, status="cancelled", fee="1500", **kw),
        "someone_else": job(db, theirs, status="delivered", fee="9999", delivered_ago=timedelta(minutes=1), **kw),
    }
    return rider, other, customer, jobs


def test_history_lists_only_my_finished_jobs(client, world):
    rider, _, _, jobs = world
    r = client.get("/api/v1/deliveries/mine/history", headers=auth(rider))
    assert r.status_code == 200, r.text
    ids = [d["id"] for d in r.json()]
    assert set(ids) == {str(jobs["today"].id), str(jobs["old"].id), str(jobs["cancelled"].id)}
    assert ids.index(str(jobs["today"].id)) < ids.index(str(jobs["old"].id))  # newest first
    assert next(d for d in r.json() if d["id"] == str(jobs["today"].id))["delivered_at"]


def test_earnings_count_only_my_delivered_jobs(client, world):
    rider, *_ = world
    e = client.get("/api/v1/deliveries/mine/earnings", headers=auth(rider)).json()
    assert e["today"] == {"amount": 2500.0, "deliveries": 1}
    assert e["all_time"] == {"amount": 6500.0, "deliveries": 2}
    assert e["week"]["amount"] >= 2500.0 and e["currency"] == "NGN"


def test_rider_dashboard_is_about_jobs(client, world):
    rider, *_ = world
    cards = {c["kind"]: c["value"] for c in client.get("/api/v1/dashboard", headers=auth(rider)).json()}
    assert cards["active"] == 1 and cards["delivered_today"] == 1
    assert cards["earned_week"].startswith("₦") and cards["rating"] == "4.8 ★"


def test_other_roles_cannot_read_rider_work(client, world):
    _, _, customer, _ = world
    assert client.get("/api/v1/deliveries/mine/history", headers=auth(customer)).status_code == 403
    assert client.get("/api/v1/deliveries/mine/earnings", headers=auth(customer)).status_code == 403


def test_track_page_shows_the_riders_live_sharing(client, world, monkeypatch):
    """GET /orders/{id}/tracking (the Track pages) uses the rider's live position while in transit."""
    rider, _, customer, jobs = world
    active = jobs["active"]  # in_transit
    monkeypatch.setattr("app.services.delivery_position.read_position", lambda delivery_id: {
        "latitude": 6.4602, "longitude": 3.4511, "accuracy_m": 12, "recorded_at": "2026-11-15T09:00:00+00:00",
        "freshness": "live", "age_seconds": 4, "sharing": True})
    r = client.get(f"/api/v1/orders/{active.order_id}/tracking", headers=auth(customer))
    assert r.status_code == 200, r.text
    snap = r.json()["tracking"]
    assert (snap["current_latitude"], snap["current_longitude"], snap["is_stale"]) == (6.4602, 3.4511, False)


def test_track_page_ignores_an_old_point(client, world, monkeypatch):
    rider, _, customer, jobs = world
    monkeypatch.setattr("app.services.delivery_position.read_position", lambda delivery_id: {
        "latitude": 6.4, "longitude": 3.4, "accuracy_m": 12, "recorded_at": "2026-11-15T08:00:00+00:00",
        "freshness": "last_known", "age_seconds": 900, "sharing": False})
    r = client.get(f"/api/v1/orders/{jobs['active'].order_id}/tracking", headers=auth(customer))
    assert r.json()["tracking"] is None
