"""Masked calls: only order parties can call, numbers never leak, webhook bridges correctly."""
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.integrations.voice import africastalking as voice
from app.main import app
from app.models.call_session import CallSession
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.order import Order
from app.models.professional import Professional
from app.services.masked_call_service import normalize_phone

SECRET = "test-voice-secret"
PHONES = {"buyer": "08031110001", "seller": "+2348031110002", "rider": "0803 111 0003", "recipient": "08031110009"}


@pytest.fixture()
def call_setup(db, make_user, monkeypatch):
    limiter.reset()
    monkeypatch.setattr(settings, "VOICE_PROVIDER", "sandbox")
    monkeypatch.setattr(settings, "VOICE_WEBHOOK_SECRET", SECRET)
    monkeypatch.setattr(settings, "AT_VOICE_NUMBER", "+2347000000000")
    buyer = make_user(role="customer", full_name="Ada Obi", phone_number=PHONES["buyer"])
    seller = make_user(role="tailor", full_name="Kemi Adeyemi", phone_number=PHONES["seller"])
    rider = make_user(role="delivery_partner", full_name="Sola Bello", phone_number=PHONES["rider"])
    stranger = make_user(role="customer", phone_number="08039999999")
    db.add(Professional(user_id=seller.id, professional_type="tailor", business_name="Kemi Couture", is_verified=True))
    partner = DeliveryPartner(user_id=rider.id, vehicle_type="bike", is_verified=True)
    db.add(partner)
    order = Order(order_number="CL-" + uuid.uuid4().hex[:20], order_type="customer_order",
                  buyer_user_id=buyer.id, seller_user_id=seller.id, status="shipped",
                  subtotal=Decimal(100), total_amount=Decimal(100), currency="NGN",
                  delivery_address_snapshot={"recipient_name": "Ada", "recipient_phone": PHONES["recipient"]})
    db.add(order)
    db.flush()
    db.add(Delivery(order_id=order.id, delivery_request_id=uuid.uuid4(), status="in_transit",
                    provider="internal", delivery_fee=0, delivery_partner_id=partner.id))
    db.commit()
    current = [buyer]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield {"http": http, "current": current, "order": order, "buyer": buyer, "seller": seller,
               "rider": rider, "stranger": stranger, "db": db}
    app.dependency_overrides.clear()


def test_phone_normalization():
    assert normalize_phone("0803 111 0003") == "+2348031110003"
    assert normalize_phone("+234 (803) 111-0002") == "+2348031110002"
    assert normalize_phone("002348031110002") == "+2348031110002"
    assert normalize_phone("12") is None and normalize_phone(None) is None


def test_contacts_list_callable_parties_without_numbers(call_setup):
    http, order = call_setup["http"], call_setup["order"]
    response = http.get(f"/api/v1/calls/orders/{order.id}/contacts")
    assert response.status_code == 200, response.text
    contacts = {c["party"]: c for c in response.json()}
    assert contacts["seller"]["display_name"] == "Kemi Couture"
    assert contacts["rider"]["display_name"] == "Sola"
    assert all(c["available"] for c in contacts.values())
    for phone in PHONES.values():
        assert normalize_phone(phone)[-10:] not in response.text


def test_only_order_parties_can_call_and_strangers_learn_nothing(call_setup):
    http, current, order = call_setup["http"], call_setup["current"], call_setup["order"]
    current[0] = call_setup["stranger"]
    assert http.get(f"/api/v1/calls/orders/{order.id}/contacts").status_code == 404
    assert http.post("/api/v1/calls", json={"order_id": str(order.id), "callee": "seller"}).status_code == 404
    current[0] = call_setup["buyer"]
    assert http.post("/api/v1/calls", json={"order_id": str(order.id), "callee": "buyer"}).status_code == 403


def test_customer_call_rings_their_own_phone_then_bridges_to_tailor(call_setup, monkeypatch):
    http, db, order = call_setup["http"], call_setup["db"], call_setup["order"]
    rung = {}
    monkeypatch.setattr(voice, "place_call", lambda *, to_phone, client_request_id: rung.update(to=to_phone) or "AT-session-1")

    response = http.post("/api/v1/calls", json={"order_id": str(order.id), "callee": "seller"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["callee_display_name"] == "Kemi Couture" and body["your_phone_ending"] == "01"
    assert rung["to"] == "+2348031110001"
    assert "2348031110002" not in response.text

    xml = http.post(f"/api/v1/calls/voice/{SECRET}",
                    data={"isActive": "1", "sessionId": "AT-session-1", "direction": "Outbound"})
    assert xml.status_code == 200 and xml.headers["content-type"].startswith("application/xml")
    assert 'phoneNumbers="+2348031110002"' in xml.text
    assert 'callerId="+2347000000000"' in xml.text and 'record="false"' in xml.text

    http.post(f"/api/v1/calls/voice/{SECRET}",
              data={"isActive": "0", "sessionId": "AT-session-1", "durationInSeconds": "74"})
    session = db.query(CallSession).filter_by(provider_session_id="AT-session-1").one()
    assert session.status == "completed" and session.duration_seconds == 74


def test_rider_reaches_the_delivery_recipient_and_callback_routes_back(call_setup, monkeypatch):
    http, current, order = call_setup["http"], call_setup["current"], call_setup["order"]
    monkeypatch.setattr(voice, "place_call", lambda *, to_phone, client_request_id: "AT-rider-1")
    current[0] = call_setup["rider"]
    assert http.post("/api/v1/calls", json={"order_id": str(order.id), "callee": "buyer"}).status_code == 201
    xml = http.post(f"/api/v1/calls/voice/{SECRET}", data={"isActive": "1", "sessionId": "AT-rider-1"})
    assert 'phoneNumbers="+2348031110009"' in xml.text  # checkout recipient, not the account phone

    # The recipient rings Tailora's number back: route them to the rider who called.
    back = http.post(f"/api/v1/calls/voice/{SECRET}", data={
        "isActive": "1", "sessionId": "inbound-1", "direction": "Inbound", "callerNumber": "+2348031110009"})
    assert 'phoneNumbers="+2348031110003"' in back.text

    unknown = http.post(f"/api/v1/calls/voice/{SECRET}", data={
        "isActive": "1", "sessionId": "inbound-2", "direction": "Inbound", "callerNumber": "+2348000000000"})
    assert "<Dial" not in unknown.text and "Tailora app" in unknown.text


def test_closed_orders_and_missing_numbers_block_calls(call_setup):
    http, db, order, current = call_setup["http"], call_setup["db"], call_setup["order"], call_setup["current"]
    order.status = "completed"
    db.commit()
    assert http.post("/api/v1/calls", json={"order_id": str(order.id), "callee": "seller"}).status_code == 409
    order.status = "shipped"
    call_setup["buyer"].phone_number = None
    db.commit()
    response = http.post("/api/v1/calls", json={"order_id": str(order.id), "callee": "seller"})
    assert response.status_code == 422 and "Settings" in response.text
    current[0] = call_setup["seller"]
    contacts = {c["party"]: c for c in http.get(f"/api/v1/calls/orders/{order.id}/contacts").json()}
    # Sellers reach the buyer's own account number, which is now missing.
    assert contacts["buyer"]["available"] is False
    assert "phone number" in contacts["buyer"]["reason"]


def test_webhook_rejects_wrong_secret_and_unconfigured_calling(call_setup, monkeypatch):
    http, order = call_setup["http"], call_setup["order"]
    assert http.post("/api/v1/calls/voice/wrong", data={"isActive": "1"}).status_code == 404
    monkeypatch.setattr(settings, "VOICE_PROVIDER", None)
    response = http.post("/api/v1/calls", json={"order_id": str(order.id), "callee": "seller"})
    assert response.status_code == 503
    contacts = http.get(f"/api/v1/calls/orders/{order.id}/contacts").json()
    assert all(not c["available"] for c in contacts)


def test_customer_tracking_no_longer_returns_rider_phone(call_setup):
    http, order = call_setup["http"], call_setup["order"]
    body = http.get(f"/api/v1/deliveries/orders/{order.id}/tracking")
    assert body.status_code == 200
    assert "rider_phone" not in body.text and "2348031110003" not in body.text


def test_call_attempts_are_rate_limited(call_setup):
    http, order = call_setup["http"], call_setup["order"]
    statuses = [http.post("/api/v1/calls", json={"order_id": str(order.id), "callee": "seller"}).status_code
                for _ in range(7)]
    assert statuses[:6] == [201] * 6 and statuses[6] == 429
