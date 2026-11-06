"""Logistics phase 6: external courier companies behind one contract (sandbox courier only)."""
import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.core.timezone import utcnow
from app.integrations.couriers import enabled_couriers
from app.integrations.couriers.base import CourierError
from app.integrations.couriers.sandbox import SandboxCourier, sign
from app.main import app
from app.models.audit_log import AuditLog
from app.models.courier_event import CourierEventRecord
from app.models.delivery import Delivery
from app.models.delivery_request import DeliveryRequest
from app.models.location import Location
from app.models.order import Order


@pytest.fixture(autouse=True)
def sandbox_on(monkeypatch):
    monkeypatch.setattr(settings, "EXTERNAL_COURIERS", ["sandbox"])
    monkeypatch.setattr(settings, "SANDBOX_COURIER_WEBHOOK_SECRET", "test-webhook-secret-123")
    limiter.reset()


@pytest.fixture()
def desk(db, make_user):
    seller, buyer, admin = make_user(role="tailor"), make_user(), make_user(role="admin")
    pickup = Location(location_type="delivery_pickup", latitude=6.5095, longitude=3.3711, formatted_address="Yaba")
    dropoff = Location(location_type="delivery_dropoff", latitude=6.4474, longitude=3.4728, formatted_address="Lekki")
    order = Order(order_number="EX-" + uuid.uuid4().hex[:8].upper(), order_type="customer_order",
                  buyer_user_id=buyer.id, seller_user_id=seller.id, status="ready_for_delivery",
                  subtotal=40000, total_amount=40000, currency="NGN", ordered_at=utcnow())
    db.add_all([pickup, dropoff, order])
    db.flush()
    req = DeliveryRequest(order_id=order.id, pickup_location_id=pickup.id, dropoff_location_id=dropoff.id,
                          status="requested", proposed_fee=2500)
    db.add(req)
    db.commit()
    current = [admin]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield {"http": http, "current": current, "db": db, "order": order, "request": req, "seller": seller}
    app.dependency_overrides.clear()


def _book(desk):
    http, req = desk["http"], desk["request"]
    quotes = http.get(f"/api/v1/admin/dispatch/requests/{req.id}/courier-quotes").json()
    quote = next(q for q in quotes if q["courier"] == "sandbox")
    booked = http.post(f"/api/v1/admin/dispatch/requests/{req.id}/courier-booking",
                       json={"courier": "sandbox", "quote_id": quote["quote_id"], "reason": "No riders free in Yaba"})
    assert booked.status_code == 200, booked.text
    return quote, booked.json()


def _webhook(desk, external_id, status, *, event_id=None, secret_ok=True):
    body = json.dumps({"id": event_id or f"evt_{uuid.uuid4().hex[:8]}", "shipment_id": external_id, "status": status,
                       "occurred_at": utcnow().isoformat(), "courier": "Test Rider",
                       "proof_url": "https://sandbox-courier.test/pod.jpg" if status == "delivered" else None}).encode()
    signature = sign(body) if secret_ok else "0" * 64
    return desk["http"].post("/api/v1/webhooks/couriers/sandbox", content=body,
                             headers={"X-Sandbox-Signature": signature, "Content-Type": "application/json"})


def test_quote_book_and_deliver_through_signed_webhooks(desk):
    db, order = desk["db"], desk["order"]
    quote, booked = _book(desk)
    assert quote["available"] and quote["amount_ngn"] > 1500 and quote["eta_minutes"]
    delivery = db.get(Delivery, uuid.UUID(booked["delivery_id"]))
    assert delivery.provider == "sandbox" and delivery.delivery_partner_id is None
    assert float(delivery.delivery_fee) == quote["amount_ngn"]  # recorded only; nothing is charged
    assert db.query(AuditLog).filter_by(action="dispatch.courier_booked").count() == 1

    assert _webhook(desk, booked["external_id"], "picked_up").json()["outcome"] == "applied"
    db.refresh(order)
    assert order.status == "out_for_delivery"
    done = _webhook(desk, booked["external_id"], "delivered")
    assert done.json()["outcome"] == "applied"
    db.refresh(order)
    db.refresh(delivery)
    assert order.status == "delivered" and delivery.status == "delivered"
    assert delivery.proof_of_delivery_url == "https://sandbox-courier.test/pod.jpg"


def test_forged_duplicate_and_backwards_updates_change_nothing(desk):
    db, order = desk["db"], desk["order"]
    _, booked = _book(desk)
    assert _webhook(desk, booked["external_id"], "delivered", secret_ok=False).status_code == 401
    db.refresh(order)
    assert order.status == "ready_for_delivery"
    first = _webhook(desk, booked["external_id"], "picked_up", event_id="evt_same")
    again = _webhook(desk, booked["external_id"], "picked_up", event_id="evt_same")
    assert first.json()["outcome"] == "applied" and again.json()["outcome"] == "duplicate"
    assert db.query(CourierEventRecord).filter_by(event_id="evt_same").count() == 1
    assert _webhook(desk, booked["external_id"], "courier_assigned").json()["outcome"] == "ignored"  # backwards
    assert _webhook(desk, "sbx_unknown", "delivered").json()["outcome"] == "unmatched"


def test_no_double_booking_and_price_changes_are_refused(desk, monkeypatch):
    http, req = desk["http"], desk["request"]
    _book(desk)
    again = http.post(f"/api/v1/admin/dispatch/requests/{req.id}/courier-booking",
                      json={"courier": "sandbox", "quote_id": "sbxq_x_9999", "reason": "Booking twice"})
    assert again.status_code == 409


def test_stale_quote_and_courier_outage_leave_no_trace(desk, monkeypatch, db):
    http, req = desk["http"], desk["request"]
    stale = http.post(f"/api/v1/admin/dispatch/requests/{req.id}/courier-booking",
                      json={"courier": "sandbox", "quote_id": "sbxq_old_100", "reason": "Old price"})
    assert stale.status_code == 409 and "changed" in stale.text

    def down(*a, **k):
        raise CourierError("timeout")
    monkeypatch.setattr(SandboxCourier, "book", down)
    quote = http.get(f"/api/v1/admin/dispatch/requests/{req.id}/courier-quotes").json()[0]
    failed = http.post(f"/api/v1/admin/dispatch/requests/{req.id}/courier-booking",
                       json={"courier": "sandbox", "quote_id": quote["quote_id"], "reason": "Courier down"})
    assert failed.status_code == 409
    db.refresh(req)
    assert req.status == "requested" and db.query(Delivery).filter_by(order_id=req.order_id).count() == 0


def test_reconciliation_catches_a_missed_webhook_and_cancel_before_pickup(desk):
    db, http = desk["db"], desk["http"]
    _, booked = _book(desk)
    courier = enabled_couriers()["sandbox"]
    courier.make_webhook(booked["external_id"], "picked_up")  # courier moved on; webhook "lost"
    from app.services.external_courier_service import ExternalCourierService
    assert ExternalCourierService(db).reconcile() == 1
    delivery = db.get(Delivery, uuid.UUID(booked["delivery_id"]))
    db.refresh(delivery)
    assert delivery.status == "in_transit"
    refused = http.post(f"/api/v1/admin/dispatch/deliveries/{delivery.id}/courier-cancel",
                        json={"reason": "Customer asked"})
    assert refused.status_code == 409  # already collected


def test_cancel_before_pickup_reopens_the_job(desk):
    db, http, req = desk["db"], desk["http"], desk["request"]
    _, booked = _book(desk)
    cancelled = http.post(f"/api/v1/admin/dispatch/deliveries/{booked['delivery_id']}/courier-cancel",
                          json={"reason": "A rider became free"})
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    db.refresh(req)
    assert req.status == "requested"


def test_couriers_are_off_by_default_and_the_sandbox_never_runs_in_production(desk, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    assert enabled_couriers() == {}
    monkeypatch.setattr(settings, "APP_ENV", "test")
    monkeypatch.setattr(settings, "EXTERNAL_COURIERS", [])
    assert desk["http"].get(f"/api/v1/admin/dispatch/requests/{desk['request'].id}/courier-quotes").json() == []
    assert desk["http"].post("/api/v1/webhooks/couriers/sandbox", content=b"{}").status_code == 404
    desk["current"][0] = desk["seller"]
    monkeypatch.setattr(settings, "EXTERNAL_COURIERS", ["sandbox"])
    assert desk["http"].get(f"/api/v1/admin/dispatch/requests/{desk['request'].id}/courier-quotes").status_code == 403
