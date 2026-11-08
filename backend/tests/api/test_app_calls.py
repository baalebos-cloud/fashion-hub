"""In-app calls: only order parties, one room per call, ring/answer/decline/cancel/end, missed calls."""
import uuid
from datetime import timedelta
from decimal import Decimal

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.main import app
from app.models.call_session import CallSession
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.notification import Notification
from app.models.order import Order
from app.models.professional import Professional

KEY, SECRET, URL = "APItest", "s" * 40, "wss://tailora-test.livekit.cloud"


@pytest.fixture()
def ctx(db, make_user, monkeypatch):
    limiter.reset()
    monkeypatch.setattr(settings, "LIVEKIT_URL", URL)
    monkeypatch.setattr(settings, "LIVEKIT_API_KEY", KEY)
    monkeypatch.setattr(settings, "LIVEKIT_API_SECRET", SECRET)
    monkeypatch.setattr(settings, "VOICE_PROVIDER", None)
    # Nobody has a phone number: in-app calls must not need one.
    buyer = make_user(role="customer", full_name="Ada Obi")
    seller = make_user(role="tailor", full_name="Kemi Adeyemi")
    rider = make_user(role="delivery_partner", full_name="Sola Bello")
    stranger = make_user(role="customer")
    db.add(Professional(user_id=seller.id, professional_type="tailor", business_name="Kemi Couture", is_verified=True))
    partner = DeliveryPartner(user_id=rider.id, vehicle_type="bike", is_verified=True)
    db.add(partner)
    order = Order(order_number="TL-" + uuid.uuid4().hex[:8].upper(), order_type="customer_order", buyer_user_id=buyer.id,
                  seller_user_id=seller.id, status="out_for_delivery", subtotal=Decimal(100), total_amount=Decimal(100), currency="NGN")
    db.add(order)
    db.flush()
    db.add(Delivery(order_id=order.id, delivery_request_id=uuid.uuid4(), status="in_transit", provider="internal",
                    delivery_fee=0, delivery_partner_id=partner.id))
    db.commit()
    current = [buyer]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield dict(http=http, db=db, current=current, order=order, buyer=buyer, seller=seller, rider=rider, stranger=stranger)
    app.dependency_overrides.clear()


def as_(ctx, who):
    ctx["current"][0] = ctx[who]
    return ctx["http"]


def start(ctx, who="buyer", callee="seller"):
    return as_(ctx, who).post("/api/v1/calls/app", json={"order_id": str(ctx["order"].id), "callee": callee})


def claims(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_aud": False})


def test_contacts_are_callable_without_phone_numbers(ctx):
    contacts = {c["party"]: c for c in as_(ctx, "buyer").get(f"/api/v1/calls/orders/{ctx['order'].id}/contacts").json()}
    assert contacts["seller"]["available"] and contacts["rider"]["available"]
    assert contacts["seller"]["reason"] is None


def test_full_call_ring_answer_end(ctx):
    started = start(ctx)
    assert started.status_code == 201, started.text
    call = started.json()
    assert call["status"] == "ringing" and call["other_party_name"] == "Kemi Couture" and call["url"] == URL
    caller_claims = claims(call["token"])
    assert caller_claims["iss"] == KEY and caller_claims["sub"] == str(ctx["buyer"].id)
    assert caller_claims["video"]["roomJoin"] and caller_claims["video"]["canPublishSources"] == ["microphone"]
    room = caller_claims["video"]["room"]
    assert room.startswith("call-") and len(room) > 30  # unguessable

    ringing = as_(ctx, "seller").get("/api/v1/calls/app/incoming").json()
    assert [c["call_id"] for c in ringing] == [call["call_id"]]
    assert ringing[0]["other_party_name"] == "Ada" and "token" not in ringing[0]

    answered = as_(ctx, "seller").post(f"/api/v1/calls/app/{call['call_id']}/answer")
    assert answered.status_code == 200, answered.text
    assert claims(answered.json()["token"])["video"]["room"] == room
    assert as_(ctx, "buyer").get(f"/api/v1/calls/app/{call['call_id']}").json()["status"] == "active"

    ended = as_(ctx, "buyer").post(f"/api/v1/calls/app/{call['call_id']}/end").json()
    assert ended["status"] == "ended"
    record = ctx["db"].get(CallSession, uuid.UUID(call["call_id"]))
    assert record.duration_seconds is not None and record.ended_at is not None
    assert as_(ctx, "seller").post(f"/api/v1/calls/app/{call['call_id']}/end").status_code == 200  # repeat is harmless


def test_decline_and_cancel(ctx):
    call = start(ctx).json()
    assert as_(ctx, "buyer").post(f"/api/v1/calls/app/{call['call_id']}/answer").status_code == 403  # caller can't answer
    assert as_(ctx, "seller").post(f"/api/v1/calls/app/{call['call_id']}/decline").json()["status"] == "declined"
    assert as_(ctx, "seller").post(f"/api/v1/calls/app/{call['call_id']}/answer").status_code == 409
    second = start(ctx).json()
    assert as_(ctx, "buyer").post(f"/api/v1/calls/app/{second['call_id']}/cancel").json()["status"] == "cancelled"
    assert as_(ctx, "seller").get("/api/v1/calls/app/incoming").json() == []


def test_unanswered_call_becomes_missed_with_a_notification(ctx):
    call = start(ctx).json()
    record = ctx["db"].get(CallSession, uuid.UUID(call["call_id"]))
    record.created_at = record.created_at - timedelta(seconds=settings.APP_CALL_RING_SECONDS + 5)
    ctx["db"].commit()
    assert as_(ctx, "seller").get("/api/v1/calls/app/incoming").json() == []
    assert as_(ctx, "buyer").get(f"/api/v1/calls/app/{call['call_id']}").json()["status"] == "missed"
    notes = ctx["db"].query(Notification).filter_by(recipient_user_id=ctx["seller"].id, event_type="call.missed").all()
    assert len(notes) == 1 and ctx["order"].order_number in notes[0].body
    assert as_(ctx, "seller").post(f"/api/v1/calls/app/{call['call_id']}/answer").status_code == 409


def test_busy_people_cannot_be_rung_twice(ctx):
    start(ctx)
    busy = start(ctx, who="rider", callee="seller")
    assert busy.status_code == 409 and "another call" in busy.text
    assert start(ctx).status_code == 409  # the caller is already on a call


def test_rider_can_call_the_customer_and_the_tailor(ctx):
    assert start(ctx, who="rider", callee="buyer").status_code == 201


def test_strangers_and_closed_orders(ctx):
    assert start(ctx, who="stranger").status_code == 404
    call = start(ctx).json()
    assert as_(ctx, "stranger").get(f"/api/v1/calls/app/{call['call_id']}").status_code == 404
    assert as_(ctx, "stranger").post(f"/api/v1/calls/app/{call['call_id']}/answer").status_code == 404
    as_(ctx, "buyer").post(f"/api/v1/calls/app/{call['call_id']}/cancel")
    ctx["order"].status = "completed"
    ctx["db"].commit()
    assert start(ctx).status_code == 409


def test_not_set_up_means_no_calls_and_no_ringing(ctx, monkeypatch):
    monkeypatch.setattr(settings, "LIVEKIT_API_SECRET", None)
    assert start(ctx).status_code == 503
    assert as_(ctx, "seller").get("/api/v1/calls/app/incoming").json() == []
    contacts = as_(ctx, "buyer").get(f"/api/v1/calls/orders/{ctx['order'].id}/contacts").json()
    assert not any(c["available"] for c in contacts)
