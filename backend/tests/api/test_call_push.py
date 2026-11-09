"""Ringing alerts on phones: what is sent to Apple/Firebase, when, and dead-token clean-up."""
import json
import uuid
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.core.timezone import utcnow
from app.integrations.notifications import mobile_push
from app.integrations.notifications.mobile_push import PushMessage
from app.main import app
from app.models.call_session import CallSession
from app.models.device_token import DeviceToken
from app.models.order import Order
from app.models.professional import Professional
from app.services import call_push


def _p8():
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    return key, pem


@pytest.fixture()
def ctx(db, make_user, monkeypatch):
    limiter.reset()
    for k, v in {"LIVEKIT_URL": "wss://t.livekit.cloud", "LIVEKIT_API_KEY": "K", "LIVEKIT_API_SECRET": "s" * 40,
                 "APNS_KEY_ID": "KEY123", "APNS_TEAM_ID": "TEAM123", "FCM_PROJECT_ID": "tailora-test",
                 "FCM_SERVICE_ACCOUNT_JSON": "{}"}.items():
        monkeypatch.setattr(settings, k, v)
    monkeypatch.setattr(settings, "APNS_PRIVATE_KEY", _p8()[1])
    buyer, seller = make_user(full_name="Ada Obi"), make_user(role="tailor", full_name="Kemi Adeyemi")
    db.add(Professional(user_id=seller.id, professional_type="tailor", business_name="Kemi Couture", is_verified=True))
    order = Order(order_number="TL-" + uuid.uuid4().hex[:6].upper(), order_type="customer_order", buyer_user_id=buyer.id,
                  seller_user_id=seller.id, status="in_production", subtotal=Decimal(1), total_amount=Decimal(1), currency="NGN")
    db.add(order)
    db.add_all([DeviceToken(user_id=seller.id, platform="ios", token="a" * 64, last_seen_at=utcnow()),
                DeviceToken(user_id=seller.id, platform="android", token="fcm-token-" + "b" * 20, last_seen_at=utcnow())])
    db.commit()
    sent: list[tuple[str, str, PushMessage]] = []
    results = {}

    def fake_send(platform, token, message):
        sent.append((platform, token, message))
        return results.get(token, "sent")
    monkeypatch.setattr(mobile_push, "send", fake_send)

    @contextmanager
    def same_session():  # background tasks use the test's transaction
        yield db
    monkeypatch.setattr(call_push, "SessionLocal", same_session)
    current = [buyer]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield dict(http=http, db=db, current=current, buyer=buyer, seller=seller, order=order, sent=sent, results=results)
    app.dependency_overrides.clear()


def _start(ctx):
    ctx["current"][0] = ctx["buyer"]
    res = ctx["http"].post("/api/v1/calls/app", json={"order_id": str(ctx["order"].id), "callee": "seller"})
    assert res.status_code == 201, res.text
    return res.json()


def test_a_new_call_rings_every_phone_of_the_person_called(ctx):
    call = _start(ctx)
    assert {p for p, _, _ in ctx["sent"]} == {"ios", "android"}
    message = ctx["sent"][0][2]
    assert message.urgent and message.title == "Ada is calling"
    assert ctx["order"].order_number in message.body
    assert message.data == {"type": "incoming_call", "call_id": call["call_id"], "order_id": str(ctx["order"].id)}
    assert message.collapse_id == f"call-{call['call_id']}" and message.ttl_seconds == 45


def test_cancelled_and_missed_calls_replace_the_ringing_alert(ctx):
    call = _start(ctx)
    ctx["sent"].clear()
    ctx["http"].post(f"/api/v1/calls/app/{call['call_id']}/cancel")
    missed = [m for _, _, m in ctx["sent"]]
    assert missed and all(m.title == "Missed call from Ada" and m.collapse_id == f"call-{call['call_id']}" and not m.urgent for m in missed)

    second = _start(ctx)
    record = ctx["db"].get(CallSession, uuid.UUID(second["call_id"]))
    record.created_at = record.created_at - timedelta(seconds=settings.APP_CALL_RING_SECONDS + 5)
    ctx["db"].commit()
    ctx["sent"].clear()
    ctx["current"][0] = ctx["seller"]
    ctx["http"].get("/api/v1/calls/app/incoming")  # discovers it timed out
    assert [m.data["type"] for _, _, m in ctx["sent"]] == ["missed_call", "missed_call"]


def test_answering_or_declining_sends_nothing_more(ctx):
    call = _start(ctx)
    ctx["sent"].clear()
    ctx["current"][0] = ctx["seller"]
    ctx["http"].post(f"/api/v1/calls/app/{call['call_id']}/decline")
    assert ctx["sent"] == []


def test_dead_phone_tokens_are_removed(ctx):
    ctx["results"]["a" * 64] = "invalid"
    _start(ctx)
    assert ctx["db"].query(DeviceToken).filter_by(user_id=ctx["seller"].id, platform="ios").count() == 0
    assert ctx["db"].query(DeviceToken).filter_by(user_id=ctx["seller"].id, platform="android").count() == 1


def test_nothing_is_sent_when_push_is_not_set_up(ctx, monkeypatch):
    for k in ("APNS_KEY_ID", "FCM_PROJECT_ID"):
        monkeypatch.setattr(settings, k, None)
    _start(ctx)
    assert ctx["sent"] == []


# ---- the two senders -----------------------------------------------------------------

def _client(status=200, body=None):
    client = MagicMock()
    client.__enter__ = lambda self: self
    client.__exit__ = lambda self, *a: False
    client.post.return_value = MagicMock(status_code=status, json=lambda: body or {})
    return client


def test_apns_request_matches_apples_spec(monkeypatch):
    key, pem = _p8()
    for k, v in {"APNS_KEY_ID": "KEY123", "APNS_TEAM_ID": "TEAM123", "APNS_PRIVATE_KEY": pem, "APNS_USE_SANDBOX": True}.items():
        monkeypatch.setattr(settings, k, v)
    monkeypatch.setattr(mobile_push, "_apns_token", None)
    client = _client()
    message = PushMessage("Ada is calling", "Tap to answer.", {"type": "incoming_call", "call_id": "c1"}, "call-c1", 45, True)
    assert mobile_push.send_apns("deadbeef", message, client=client) == "sent"
    url = client.post.call_args.args[0]
    headers, payload = client.post.call_args.kwargs["headers"], json.loads(client.post.call_args.kwargs["content"])
    assert url == "https://api.sandbox.push.apple.com/3/device/deadbeef"
    assert headers["apns-topic"] == "ng.tailora.app" and headers["apns-push-type"] == "alert" and headers["apns-priority"] == "10"
    assert headers["apns-collapse-id"] == "call-c1"
    claims = jwt.decode(headers["authorization"].split(" ", 1)[1], key.public_key(), algorithms=["ES256"])
    assert claims["iss"] == "TEAM123"
    assert jwt.get_unverified_header(headers["authorization"].split(" ", 1)[1])["kid"] == "KEY123"
    assert payload["aps"]["interruption-level"] == "time-sensitive" and payload["call_id"] == "c1"
    assert mobile_push.send_apns("dead", message, client=_client(410, {"reason": "Unregistered"})) == "invalid"
    assert mobile_push.send_apns("dead", message, client=_client(503, {"reason": "ServiceUnavailable"})) == "failed"
    # A sandbox/production mismatch must not delete the phone's registration.
    assert mobile_push.send_apns("tok", message, client=_client(400, {"reason": "BadDeviceToken"})) == "failed"


def test_fcm_request_matches_firebase_spec(monkeypatch):
    monkeypatch.setattr(settings, "FCM_PROJECT_ID", "tailora-test")
    monkeypatch.setattr(settings, "FCM_SERVICE_ACCOUNT_JSON", "{}")
    monkeypatch.setattr(mobile_push, "_fcm_access_token", lambda: "oauth-token")
    client = _client()
    message = PushMessage("Ada is calling", "Tap to answer.", {"type": "incoming_call", "call_id": "c1"}, "call-c1", 45, True)
    assert mobile_push.send_fcm("tok", message, client=client) == "sent"
    url, body = client.post.call_args.args[0], client.post.call_args.kwargs["json"]
    assert url == "https://fcm.googleapis.com/v1/projects/tailora-test/messages:send"
    android = body["message"]["android"]
    assert android["priority"] == "HIGH" and android["ttl"] == "45s"
    assert android["notification"]["channel_id"] == "calls" and android["notification"]["tag"] == "call-c1"
    assert body["message"]["data"] == {"type": "incoming_call", "call_id": "c1"}
    assert client.post.call_args.kwargs["headers"]["authorization"] == "Bearer oauth-token"
    assert mobile_push.send_fcm("tok", message, client=_client(404, {"error": {"status": "NOT_FOUND"}})) == "invalid"
