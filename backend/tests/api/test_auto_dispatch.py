"""Phase 3: sequential, exclusive auto-offers (feature-flagged), with fallback to the open board."""
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.timezone import utcnow
from app.main import app
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.dispatch_job_offer import DispatchJobOffer
from app.models.location import Location
from app.models.professional import Professional
from app.services.auto_dispatch_service import AutoDispatchService
from app.services.order_service import OrderService
from tests.catalog_helpers import catalog_request

SHOP = (6.6018, 3.3515)  # Ikeja


def _rider(db, make_user, name, *, km_north=None, verified=True, available=True, vehicle="bike"):
    user = make_user(role="delivery_partner", full_name=name)
    if km_north is not None:  # ~0.009 degrees latitude per km
        home = Location(location_type="customer_address", latitude=SHOP[0] + km_north * 0.009, longitude=SHOP[1])
        db.add(home)
        db.flush()
        user.home_location_id = home.id
    partner = DeliveryPartner(user_id=user.id, is_verified=verified, is_available=available, vehicle_type=vehicle)
    db.add(partner)
    db.flush()
    return user, partner


@pytest.fixture()
def auto(db, make_user, monkeypatch):
    monkeypatch.setattr(settings, "DISPATCH_AUTO_OFFER_ENABLED", True)
    monkeypatch.setattr(settings, "DISPATCH_AUTO_OFFER_TTL_SECONDS", 90)
    monkeypatch.setattr(settings, "DISPATCH_AUTO_OFFER_MAX_ATTEMPTS", 5)
    monkeypatch.setattr(settings, "DISPATCH_AUTO_OFFER_RADIUS_KM", 20.0)
    buyer, seller, admin = make_user(), make_user(role="tailor"), make_user(role="admin")
    order = OrderService(db).create_customer_order(**catalog_request(db, buyer, seller))
    shop = Location(location_type="tailor_shop", formatted_address="12 Shop Rd", city="Ikeja",
                    state_region="Lagos", latitude=SHOP[0], longitude=SHOP[1])
    db.add(shop)
    db.flush()
    db.query(Professional).filter_by(user_id=seller.id).one().location_id = shop.id
    order.status = "ready_for_delivery"
    riders = {
        "near": _rider(db, make_user, "Near Rider", km_north=1),
        "mid": _rider(db, make_user, "Mid Rider", km_north=8),
        "unknown": _rider(db, make_user, "Unknown Rider"),
        "far": _rider(db, make_user, "Far Rider", km_north=50),           # outside radius
        "offline": _rider(db, make_user, "Offline Rider", km_north=0.5, available=False),
        "unverified": _rider(db, make_user, "Unverified Rider", km_north=0.5, verified=False),
        "novehicle": _rider(db, make_user, "No Vehicle", km_north=0.5, vehicle=None),
    }
    db.commit()
    current = [seller]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        request_id = http.post(f"/api/v1/delivery-requests/orders/{order.id}").json()["id"]
        yield {"http": http, "current": current, "db": db, "order": order, "seller": seller, "admin": admin,
               "riders": riders, "request_id": uuid.UUID(request_id)}
    app.dependency_overrides.clear()


def _offers(db, request_id):
    return db.query(DispatchJobOffer).filter_by(delivery_request_id=request_id).order_by(DispatchJobOffer.attempt).all()


def _expire_live(db, request_id):
    live = db.query(DispatchJobOffer).filter_by(delivery_request_id=request_id, status="offered").one()
    live.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()


def test_new_job_goes_to_the_nearest_eligible_rider_exclusively(auto):
    http, current, db, rid = auto["http"], auto["current"], auto["db"], auto["request_id"]
    offers = _offers(db, rid)
    assert len(offers) == 1 and offers[0].delivery_partner_id == auto["riders"]["near"][1].id
    assert offers[0].attempt == 1 and float(offers[0].distance_km) < 2

    current[0] = auto["riders"]["mid"][0]  # another rider can't see, claim or bid on it during the window
    assert all(j["id"] != str(rid) for j in http.get("/api/v1/delivery-requests/available").json())
    claim = http.post(f"/api/v1/delivery-requests/{rid}/accept")
    assert claim.status_code == 409 and "reserved" in claim.text
    assert http.post(f"/api/v1/delivery-requests/{rid}/offers",
                     json={"amount": 2000, "eta_to_pickup_minutes": 5}).status_code == 409
    assert http.post(f"/api/v1/delivery-requests/job-offers/{offers[0].id}/accept").status_code == 404

    current[0] = auto["riders"]["near"][0]
    reserved = http.get("/api/v1/delivery-requests/job-offers/mine").json()
    assert len(reserved) == 1 and reserved[0]["job"]["pickup_area"] == "Ikeja, Lagos"
    assert "12 Shop Rd" not in str(reserved)
    accepted = http.post(f"/api/v1/delivery-requests/job-offers/{reserved[0]['id']}/accept")
    assert accepted.status_code == 200, accepted.text
    assert db.get(Delivery, uuid.UUID(accepted.json()["id"])).delivery_partner_id == auto["riders"]["near"][1].id
    db.refresh(offers[0])
    assert offers[0].status == "accepted"
    assert http.post(f"/api/v1/delivery-requests/job-offers/{offers[0].id}/accept").status_code == 409


def test_decline_and_expiry_move_down_the_ranking_and_ineligible_riders_are_skipped(auto):
    http, current, db, rid = auto["http"], auto["current"], auto["db"], auto["request_id"]
    current[0] = auto["riders"]["near"][0]
    first = _offers(db, rid)[0]
    assert http.post(f"/api/v1/delivery-requests/job-offers/{first.id}/decline").status_code == 204
    assert _offers(db, rid)[-1].delivery_partner_id == auto["riders"]["mid"][1].id

    _expire_live(db, rid)
    current[0] = auto["riders"]["mid"][0]
    assert http.get("/api/v1/delivery-requests/job-offers/mine").json() == []  # lazily expired on read
    offers = _offers(db, rid)
    assert [o.status for o in offers] == ["declined", "expired", "offered"]
    assert offers[-1].delivery_partner_id == auto["riders"]["unknown"][1].id  # unknown base ranks last

    _expire_live(db, rid)
    AutoDispatchService(db).advance_expired()
    offered_to = {o.delivery_partner_id for o in _offers(db, rid)}
    for key in ("far", "offline", "unverified", "novehicle"):
        assert auto["riders"][key][1].id not in offered_to, key
    assert not db.query(DispatchJobOffer).filter_by(delivery_request_id=rid, status="offered").count()


def test_after_max_attempts_the_job_falls_back_to_the_open_board(auto, monkeypatch):
    http, current, db, rid = auto["http"], auto["current"], auto["db"], auto["request_id"]
    monkeypatch.setattr(settings, "DISPATCH_AUTO_OFFER_MAX_ATTEMPTS", 1)
    current[0] = auto["riders"]["near"][0]
    http.post(f"/api/v1/delivery-requests/job-offers/{_offers(db, rid)[0].id}/decline")
    assert len(_offers(db, rid)) == 1
    current[0] = auto["riders"]["mid"][0]
    assert any(j["id"] == str(rid) for j in http.get("/api/v1/delivery-requests/available").json())
    assert http.post(f"/api/v1/delivery-requests/{rid}/accept").status_code == 200


def test_going_offline_passes_the_reserved_job_on(auto):
    http, current, db, rid = auto["http"], auto["current"], auto["db"], auto["request_id"]
    current[0] = auto["riders"]["near"][0]
    assert http.put("/api/v1/delivery-partners/me/availability", json={"is_available": False}).status_code == 200
    offers = _offers(db, rid)
    assert offers[0].status == "withdrawn" and offers[-1].delivery_partner_id == auto["riders"]["mid"][1].id


def test_admin_sees_who_holds_the_job_and_stopping_the_search_withdraws_it(auto):
    http, current, db, rid = auto["http"], auto["current"], auto["db"], auto["request_id"]
    current[0] = auto["admin"]
    board = http.get("/api/v1/admin/dispatch-board").json()
    row = next(p for p in board["pending"] if p["id"] == str(rid))
    assert board["auto_offers_enabled"] is True and row["offered_to"] == "Near" and row["offer_attempt"] == 1
    assert http.post(f"/api/v1/admin/dispatch/requests/{rid}/cancel", json={"reason": "Seller paused order"}).status_code == 200
    assert _offers(db, rid)[0].status == "withdrawn"
    current[0] = auto["riders"]["near"][0]
    assert http.get("/api/v1/delivery-requests/job-offers/mine").json() == []


def test_database_allows_only_one_live_offer_per_job(auto):
    db, rid = auto["db"], auto["request_id"]
    db.add(DispatchJobOffer(delivery_request_id=rid, delivery_partner_id=auto["riders"]["mid"][1].id,
                            status="offered", attempt=9, expires_at=utcnow() + timedelta(minutes=1)))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_disabled_flag_keeps_the_open_board_only(db, make_user, monkeypatch):
    monkeypatch.setattr(settings, "DISPATCH_AUTO_OFFER_ENABLED", False)
    seller, buyer = make_user(role="tailor"), make_user()
    order = OrderService(db).create_customer_order(**catalog_request(db, buyer, seller))
    shop = Location(location_type="tailor_shop", latitude=SHOP[0], longitude=SHOP[1])
    db.add(shop)
    db.flush()
    db.query(Professional).filter_by(user_id=seller.id).one().location_id = shop.id
    order.status = "ready_for_delivery"
    _rider(db, make_user, "Near Rider", km_north=1)
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: seller
    try:
        with TestClient(app) as http:
            rid = http.post(f"/api/v1/delivery-requests/orders/{order.id}").json()["id"]
    finally:
        app.dependency_overrides.clear()
    assert db.query(DispatchJobOffer).filter_by(delivery_request_id=uuid.UUID(rid)).count() == 0
