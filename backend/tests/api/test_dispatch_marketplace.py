"""Uber/InDrive-style dispatch: priced job cards, rider offers, seller choice, journey + ETA."""
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.timezone import utcnow
from app.main import app
from app.models.delivery import Delivery
from app.models.delivery_offer import DeliveryOffer
from app.models.delivery_partner import DeliveryPartner
from app.models.location import Location
from app.models.professional import Professional
from app.services.dispatch_pricing import eta_minutes, offer_bounds, suggested_fare
from app.services.order_service import OrderService
from tests.catalog_helpers import catalog_request


def test_pricing_rules():
    assert suggested_fare(None) == Decimal(1000)  # no pins -> minimum fare
    assert suggested_fare(8) == Decimal(2100)      # 500 + 150 * 10.8 road km, nearest ₦50
    assert offer_bounds(Decimal(2100)) == (Decimal(1700), Decimal(4200))
    assert eta_minutes(8, "bike") == 29 and eta_minutes(8, "car") > eta_minutes(8, "bike")


@pytest.fixture()
def dispatch(db, make_user):
    buyer, seller = make_user(), make_user(role="tailor")
    rider_a = make_user(role="delivery_partner", full_name="Sola Bello")
    rider_b = make_user(role="delivery_partner", full_name="Tayo Ade")
    order = OrderService(db).create_customer_order(**catalog_request(db, buyer, seller))
    shop = Location(location_type="tailor_shop", formatted_address="12 Shop Rd, Ikeja",
                    city="Ikeja", state_region="Lagos", latitude=6.6018, longitude=3.3515)
    db.add(shop)
    db.flush()
    db.query(Professional).filter_by(user_id=seller.id).one().location_id = shop.id
    # Dispatch reads the order's checkout snapshot (authoritative), so pin it there.
    order.delivery_address_snapshot = {**(order.delivery_address_snapshot or {}),
                                       "latitude": 6.4281, "longitude": 3.4219, "city": "Victoria Island"}
    order.status = "ready_for_delivery"
    partner_a = DeliveryPartner(user_id=rider_a.id, is_verified=True, is_available=True, vehicle_type="bike")
    partner_b = DeliveryPartner(user_id=rider_b.id, is_verified=True, is_available=True, vehicle_type="car")
    db.add_all([partner_a, partner_b])
    db.commit()
    current = [seller]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        request = http.post(f"/api/v1/delivery-requests/orders/{order.id}")
        assert request.status_code == 201, request.text
        yield {"http": http, "current": current, "db": db, "order": order, "buyer": buyer, "seller": seller,
               "rider_a": rider_a, "rider_b": rider_b, "partner_a": partner_a, "partner_b": partner_b,
               "request_id": request.json()["id"]}
    app.dependency_overrides.clear()


def test_riders_see_priced_job_cards_without_private_details(dispatch):
    http, current = dispatch["http"], dispatch["current"]
    current[0] = dispatch["rider_a"]
    jobs = http.get("/api/v1/delivery-requests/available")
    assert jobs.status_code == 200, jobs.text
    job = jobs.json()[0]
    assert job["pickup_area"] == "Ikeja, Lagos" and job["dropoff_area"] == "Victoria Island, Lagos"
    assert job["approx_road_km"] > 20 and job["suggested_fare"] >= 3000
    assert job["offer_min"] < job["suggested_fare"] < job["offer_max"]
    for private in ("12 Shop Rd", "10 Test Street", "Test Customer", "+234", "6.6018", "3.4219"):
        assert private not in jobs.text


def test_instant_claim_charges_the_suggested_fare(dispatch):
    http, current, db = dispatch["http"], dispatch["current"], dispatch["db"]
    current[0] = dispatch["rider_a"]
    fare = http.get("/api/v1/delivery-requests/available").json()[0]["suggested_fare"]
    claimed = http.post(f"/api/v1/delivery-requests/{dispatch['request_id']}/accept")
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["delivery_fee"] == fare > 0


def test_riders_bid_and_the_seller_picks_one(dispatch):
    http, current, db = dispatch["http"], dispatch["current"], dispatch["db"]
    request_id = dispatch["request_id"]
    current[0] = dispatch["rider_a"]
    job = http.get("/api/v1/delivery-requests/available").json()[0]
    too_low = http.post(f"/api/v1/delivery-requests/{request_id}/offers",
                        json={"amount": job["offer_min"] - 50, "eta_to_pickup_minutes": 10})
    assert too_low.status_code == 422
    offer_a = http.post(f"/api/v1/delivery-requests/{request_id}/offers",
                        json={"amount": job["suggested_fare"] + 500, "eta_to_pickup_minutes": 8})
    assert offer_a.status_code == 201, offer_a.text
    current[0] = dispatch["rider_b"]
    offer_b = http.post(f"/api/v1/delivery-requests/{request_id}/offers",
                        json={"amount": job["suggested_fare"], "eta_to_pickup_minutes": 15}).json()

    # Other parties cannot see or accept offers.
    current[0] = dispatch["buyer"]
    assert http.get(f"/api/v1/delivery-requests/orders/{dispatch['order'].id}/dispatch").status_code == 403
    current[0] = dispatch["seller"]
    view = http.get(f"/api/v1/delivery-requests/orders/{dispatch['order'].id}/dispatch").json()
    assert [o["rider"]["first_name"] for o in view["offers"]] == ["Tayo", "Sola"]  # cheapest first
    assert view["offers"][0]["rider"]["vehicle_type"] == "car" and view["offers"][0]["rider"]["is_verified"]
    assert "Bello" not in str(view)

    accepted = http.post(f"/api/v1/delivery-requests/offers/{offer_b['id']}/accept")
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["delivery_fee"] == offer_b["amount"]
    assert db.get(Delivery, uuid.UUID(accepted.json()["id"])).delivery_partner_id == dispatch["partner_b"].id
    statuses = {o.delivery_partner_id: o.status for o in db.query(DeliveryOffer).all()}
    assert statuses == {dispatch["partner_b"].id: "accepted", dispatch["partner_a"].id: "declined"}
    assert http.post(f"/api/v1/delivery-requests/offers/{offer_a.json()['id']}/accept").status_code == 409


def test_expired_or_unavailable_offers_cannot_be_accepted(dispatch):
    http, current, db = dispatch["http"], dispatch["current"], dispatch["db"]
    current[0] = dispatch["rider_a"]
    job = http.get("/api/v1/delivery-requests/available").json()[0]
    offer = http.post(f"/api/v1/delivery-requests/{dispatch['request_id']}/offers",
                      json={"amount": job["suggested_fare"], "eta_to_pickup_minutes": 5}).json()
    db.get(DeliveryOffer, uuid.UUID(offer["id"])).expires_at = utcnow() - timedelta(minutes=1)
    db.commit()
    current[0] = dispatch["seller"]
    assert http.get(f"/api/v1/delivery-requests/orders/{dispatch['order'].id}/dispatch").json()["offers"] == []
    assert http.post(f"/api/v1/delivery-requests/offers/{offer['id']}/accept").status_code == 409

    current[0] = dispatch["rider_b"]
    offer_b = http.post(f"/api/v1/delivery-requests/{dispatch['request_id']}/offers",
                        json={"amount": job["suggested_fare"], "eta_to_pickup_minutes": 5}).json()
    dispatch["partner_b"].is_available = False
    db.commit()
    current[0] = dispatch["seller"]
    response = http.post(f"/api/v1/delivery-requests/offers/{offer_b['id']}/accept")
    assert response.status_code == 409 and "no longer available" in response.text


def test_rider_can_withdraw_an_offer(dispatch):
    http, current = dispatch["http"], dispatch["current"]
    current[0] = dispatch["rider_a"]
    job = http.get("/api/v1/delivery-requests/available").json()[0]
    http.post(f"/api/v1/delivery-requests/{dispatch['request_id']}/offers",
              json={"amount": job["suggested_fare"], "eta_to_pickup_minutes": 5})
    assert http.get("/api/v1/delivery-requests/available").json()[0]["my_offer"]["status"] == "pending"
    assert http.delete(f"/api/v1/delivery-requests/{dispatch['request_id']}/offers/mine").status_code == 204
    assert http.get("/api/v1/delivery-requests/available").json()[0]["my_offer"]["status"] == "withdrawn"


def test_journey_milestones_and_live_eta(dispatch):
    http, current, db, order = dispatch["http"], dispatch["current"], dispatch["db"], dispatch["order"]
    current[0] = dispatch["rider_a"]
    delivery_id = http.post(f"/api/v1/delivery-requests/{dispatch['request_id']}/accept").json()["id"]

    current[0] = dispatch["buyer"]
    journey = http.get(f"/api/v1/deliveries/orders/{order.id}/journey").json()
    states = {m["key"]: m["state"] for m in journey["milestones"]}
    assert journey["tracking_number"] == order.order_number
    assert states["rider_assigned"] == "done" and states["picked_up"] == "current"
    assert states["delivered"] == "upcoming" and journey["live"] is None
    assert any(m["label"] == "Rider assigned: Sola" for m in journey["milestones"])

    delivery = db.get(Delivery, uuid.UUID(delivery_id))
    delivery.status, delivery.picked_up_at = "in_transit", utcnow()
    db.commit()
    point = {"latitude": 6.4500, "longitude": 3.4000, "accuracy_m": 10, "recorded_at": "2026-11-05T12:00:00Z",
             "freshness": "live", "age_seconds": 4}
    with patch("app.services.delivery_position.read_position", return_value=point):
        live = http.get(f"/api/v1/deliveries/orders/{order.id}/journey").json()["live"]
    assert live["basis"] == "live_gps_estimate" and 1 <= live["eta_minutes"] <= 30
    assert 0 < live["distance_remaining_km"] < 10
    # A "last seen" point is never used for a live ETA.
    with patch("app.services.delivery_position.read_position", return_value={**point, "freshness": "last_known"}):
        assert http.get(f"/api/v1/deliveries/orders/{order.id}/journey").json()["live"] is None

    current[0] = dispatch["rider_b"]  # not on this order
    assert http.get(f"/api/v1/deliveries/orders/{order.id}/journey").status_code == 404
