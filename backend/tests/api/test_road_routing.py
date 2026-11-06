"""Logistics phase 1: road routing with labelled fallbacks. No real provider is ever called."""
import uuid

import httpx
import pytest
from redis import Redis

from app.core.config import settings
from app.services import route_service
from app.services.route_service import route

LEKKI = {"latitude": 6.4474, "longitude": 3.4728}
YABA = {"latitude": 6.5095, "longitude": 3.3711}


class FakeHTTP:
    """Records calls and plays back scripted responses (or exceptions)."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        return reply


def google_ok(meters=14200, seconds="1980s"):
    return httpx.Response(200, json={"routes": [{"distanceMeters": meters, "duration": seconds,
                                                 "polyline": {"encodedPolyline": "abc~xyz"}}]})


@pytest.fixture(autouse=True)
def clean_routing_state(monkeypatch):
    redis = Redis.from_url(settings.REDIS_URL)
    for key in redis.scan_iter("routing:*"):
        redis.delete(key)
    monkeypatch.setattr(route_service.time, "sleep", lambda s: None)
    monkeypatch.setattr(settings, "ROUTING_RETRIES", 1)
    yield
    for key in redis.scan_iter("routing:*"):
        redis.delete(key)


@pytest.fixture()
def google(monkeypatch):
    monkeypatch.setattr(settings, "ROUTING_PROVIDER", "google")
    monkeypatch.setattr(settings, "ROUTING_GOOGLE_API_KEY", "test-server-key")


def test_without_a_provider_answers_are_labelled_estimates():
    result = route(YABA, LEKKI, "bike")
    assert result.source == "straight_line_estimate" and result.verified is False
    assert result.fallback_reason == "no_provider" and result.distance_km > 0 and result.duration_minutes > 0


def test_google_route_is_used_cached_and_labelled(google, monkeypatch):
    fake = FakeHTTP(google_ok())
    monkeypatch.setattr(route_service.httpx, "post", fake)
    first = route(YABA, LEKKI, "car")
    assert (first.distance_km, first.duration_minutes, first.source, first.verified, first.traffic_aware) == (
        14.2, 33, "google_routes", True, True)
    assert first.polyline == "abc~xyz" and first.cached is False
    second = route(YABA, LEKKI, "car")
    assert second.cached is True and second.distance_km == 14.2 and fake.calls == 1
    assert "polyline" not in second.public()


def test_osrm_route_and_no_road_route(monkeypatch):
    monkeypatch.setattr(settings, "ROUTING_PROVIDER", "osrm")
    monkeypatch.setattr(settings, "ROUTING_OSRM_URL", "http://osrm.test")
    monkeypatch.setattr(route_service.httpx, "get", FakeHTTP(httpx.Response(200, json={
        "code": "Ok", "routes": [{"distance": 9800.0, "duration": 1260.0, "geometry": "poly"}]})))
    ok = route(YABA, LEKKI, "bike")
    assert (ok.source, ok.distance_km, ok.duration_minutes, ok.traffic_aware) == ("osrm", 9.8, 21, False)
    monkeypatch.setattr(route_service.httpx, "get", FakeHTTP(httpx.Response(400, json={"code": "NoRoute"})))
    island = route({"latitude": 6.30, "longitude": 3.50}, LEKKI, "bike")
    assert island.verified is False and island.fallback_reason == "no_road_route"


def test_timeouts_retry_once_then_fall_back_and_repeated_failures_pause_the_provider(google, monkeypatch):
    fake = FakeHTTP(httpx.ReadTimeout("slow"))
    monkeypatch.setattr(route_service.httpx, "post", fake)
    first = route(YABA, LEKKI, "bike")
    assert first.fallback_reason == "provider_unavailable" and fake.calls == 2  # one retry
    for i in range(settings.ROUTING_BREAKER_THRESHOLD):
        route({"latitude": 6.5 + i / 100, "longitude": 3.37}, LEKKI, "bike")
    calls_before = fake.calls
    paused = route({"latitude": 6.6, "longitude": 3.4}, LEKKI, "bike")
    assert paused.fallback_reason == "provider_paused" and fake.calls == calls_before  # breaker: no call
    assert route_service.health()["breaker_open"] is True


def test_rate_limit_pauses_immediately_without_retrying(google, monkeypatch):
    fake = FakeHTTP(httpx.Response(429, headers={"retry-after": "30"}))
    monkeypatch.setattr(route_service.httpx, "post", fake)
    assert route(YABA, LEKKI).fallback_reason == "provider_unavailable" and fake.calls == 1
    assert route(LEKKI, YABA).fallback_reason == "provider_paused" and fake.calls == 1


def test_a_bad_key_pauses_the_provider_and_missing_key_falls_back(google, monkeypatch):
    monkeypatch.setattr(route_service.httpx, "post", FakeHTTP(httpx.Response(403, json={"error": {}})))
    assert route(YABA, LEKKI).verified is False
    assert route_service.breaker_open("google") is True
    monkeypatch.setattr(settings, "ROUTING_GOOGLE_API_KEY", None)
    monkeypatch.setattr(settings, "ROUTING_PROVIDER", "osrm")  # different breaker, no URL
    assert route(YABA, LEKKI).fallback_reason == "provider_unavailable"


def test_live_eta_is_recomputed_at_most_once_a_minute_per_delivery(google, monkeypatch):
    fake = FakeHTTP(google_ok(5000, "600s"))
    monkeypatch.setattr(route_service.httpx, "post", fake)
    delivery = uuid.uuid4()
    first = route_service.live_route(delivery, YABA, LEKKI, "bike")
    moved = route_service.live_route(delivery, {"latitude": 6.50, "longitude": 3.38}, LEKKI, "bike")
    assert first.duration_minutes == moved.duration_minutes == 10 and moved.cached is True and fake.calls == 1


def test_missing_points_return_nothing():
    assert route(None, LEKKI) is None and route_service.live_route(uuid.uuid4(), YABA, None, "bike") is None


# ---- end to end: stored on the request, shown by role, fares unchanged by default ------------
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.core.dependencies import get_current_user  # noqa: E402
from app.main import app  # noqa: E402
from app.models.address import Address  # noqa: E402
from app.models.delivery_partner import DeliveryPartner  # noqa: E402
from app.models.location import Location  # noqa: E402
from app.models.professional import Professional  # noqa: E402
from app.services.order_service import OrderService  # noqa: E402
from tests.catalog_helpers import catalog_request  # noqa: E402


@pytest.fixture()
def dispatch(db, make_user):
    buyer, seller, rider = make_user(), make_user(role="tailor"), make_user(role="delivery_partner")
    req = catalog_request(db, buyer, seller)
    home = db.get(Location, db.get(Address, req["delivery_address_id"]).location_id)
    home.latitude, home.longitude = LEKKI["latitude"], LEKKI["longitude"]
    order = OrderService(db).create_customer_order(**req)
    shop = Location(location_type="tailor_shop", formatted_address="Yaba", city="Lagos", **YABA)
    db.add(shop)
    db.flush()
    db.query(Professional).filter_by(user_id=seller.id).one().location_id = shop.id
    order.status = "ready_for_delivery"
    db.add(DeliveryPartner(user_id=rider.id, is_verified=True, is_available=True, vehicle_type="bike"))
    db.commit()
    current = [seller]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield {"http": http, "current": current, "order": order, "seller": seller, "rider": rider, "buyer": buyer}
    app.dependency_overrides.clear()


def test_route_is_stored_once_and_shown_without_the_line_before_claiming(dispatch, google, monkeypatch):
    fake = FakeHTTP(google_ok(14200, "1980s"))
    monkeypatch.setattr(route_service.httpx, "post", fake)
    http, current = dispatch["http"], dispatch["current"]
    created = http.post(f"/api/v1/delivery-requests/orders/{dispatch['order'].id}")
    assert created.status_code == 201, created.text
    seller_view = http.get(f"/api/v1/delivery-requests/orders/{dispatch['order'].id}/dispatch").json()
    assert seller_view["request"]["route"]["source"] == "google_routes"
    current[0] = dispatch["rider"]
    jobs = http.get("/api/v1/delivery-requests/available").json()
    job = next(j for j in jobs if j["order_id"] == str(dispatch["order"].id))
    assert job["route"]["distance_km"] == 14.2 and job["route"]["duration_minutes"] == 33
    assert "abc~xyz" not in str(jobs) and fake.calls == 1  # listing never calls the provider
    delivery_id = http.post(f"/api/v1/delivery-requests/{job['id']}/accept").json()["id"]
    trip = http.get(f"/api/v1/deliveries/{delivery_id}/trip").json()
    assert trip["route"]["polyline"] == "abc~xyz" and trip["route"]["verified"] is True


def test_fares_stay_on_the_old_formula_until_the_owner_switches_road_pricing_on(dispatch, google, monkeypatch, db):
    from app.models.delivery_request import DeliveryRequest
    monkeypatch.setattr(route_service.httpx, "post", FakeHTTP(google_ok(30000, "3600s")))
    http = dispatch["http"]
    http.post(f"/api/v1/delivery-requests/orders/{dispatch['order'].id}")
    request = db.query(DeliveryRequest).filter_by(order_id=dispatch["order"].id).one()
    from app.services.dispatch_pricing import suggested_fare_for_road_km
    assert float(request.proposed_fee) != float(suggested_fare_for_road_km(30.0))  # unchanged by default
    request.status = "cancelled"
    dispatch["order"].delivery_fee = 0  # a fee already on the order is always kept
    db.commit()
    monkeypatch.setattr(settings, "DISPATCH_PRICE_FROM_ROAD_ROUTES", True)
    http.post(f"/api/v1/delivery-requests/orders/{dispatch['order'].id}")
    newest = (db.query(DeliveryRequest).filter(DeliveryRequest.order_id == dispatch["order"].id,
                                                DeliveryRequest.status != "cancelled").one())
    assert float(newest.proposed_fee) == float(suggested_fare_for_road_km(30.0))


def test_dispatch_still_works_when_the_provider_is_down(dispatch, google, monkeypatch):
    monkeypatch.setattr(route_service.httpx, "post", FakeHTTP(httpx.ConnectError("down")))
    created = dispatch["http"].post(f"/api/v1/delivery-requests/orders/{dispatch['order'].id}")
    assert created.status_code == 201
    view = dispatch["http"].get(f"/api/v1/delivery-requests/orders/{dispatch['order'].id}/dispatch").json()
    assert view["request"]["route"]["source"] == "straight_line_estimate" and view["request"]["route"]["verified"] is False


def test_admin_can_see_routing_health(dispatch, make_user):
    dispatch["current"][0] = make_user(role="admin")
    body = dispatch["http"].get("/api/v1/admin/routing/health").json()
    assert body["provider"] == "none" and "straight-line" in body["note"]
