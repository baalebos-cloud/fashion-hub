"""Confirmation emails: sent at once, links minted at send time, resend, backfill for older sign-ups."""
from datetime import timedelta
from urllib.parse import parse_qs, urlparse
import re

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ExternalProviderError
from app.core.rate_limit import limiter
from app.core.timezone import utcnow
from app.main import app
from app.models.notification import Notification
from app.services.auth_email_outbox_service import AuthEmailOutboxService


@pytest.fixture()
def mailbox(monkeypatch):
    sent = []

    def fake_send(*, to_address, subject, html_body, idempotency_key=None):
        if to_address.startswith("bounce"):
            raise ExternalProviderError("Resend rejected the email (HTTP 422).")
        sent.append({"to": to_address, "subject": subject, "html": html_body})
    monkeypatch.setattr("app.integrations.notifications.email.send_email", fake_send)
    return sent


@pytest.fixture()
def http(db):
    limiter.reset()
    current = [None]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as client:
        yield client, current
    app.dependency_overrides.clear()


def _link(html):
    return re.search(r'href="([^"]+verify-email[^"]+)"', html).group(1).replace("&amp;", "&")


def _token(html):
    return parse_qs(urlparse(_link(html)).query)["token"][0]


def test_new_signup_gets_a_branded_email_whose_link_confirms_the_account(http, db, mailbox):
    client, _ = http
    created = client.post("/api/v1/auth/signup", json={
        "email": "ada.new@example.com", "password": "Password123!", "full_name": "Ada Obi", "role": "customer"})
    assert created.status_code == 201, created.text
    job = db.query(Notification).filter_by(event_type="auth.email_verification").one()
    assert "ciphertext" not in (job.metadata_json or {})  # no token stored while queued
    assert AuthEmailOutboxService(db).send_pending()["sent"] == 1
    email = mailbox[0]
    assert email["to"] == "ada.new@example.com" and email["subject"] == "Confirm your email for Tailora"
    assert "Hi Ada" in email["html"] and "Fashion Hub" not in email["html"]
    assert client.post("/api/v1/auth/verify-email", json={"token": _token(email["html"])}).status_code == 204


def test_an_email_queued_days_ago_still_arrives_with_a_working_link(http, db, make_user, mailbox):
    client, _ = http
    user = make_user(is_email_verified=False)
    job = AuthEmailOutboxService(db).enqueue(user=user, kind="verification")
    db.commit()
    job.created_at = utcnow() - timedelta(days=9)
    db.commit()
    AuthEmailOutboxService(db).send_pending()
    assert client.post("/api/v1/auth/verify-email", json={"token": _token(mailbox[0]["html"])}).status_code == 204
    db.refresh(user)
    assert user.is_email_verified is True


def test_one_bad_address_backs_off_without_blocking_everyone_else(db, make_user, mailbox):
    bad = make_user(email="bounce-me@example.com", is_email_verified=False)
    good = make_user(email="fine@example.com", is_email_verified=False)
    service = AuthEmailOutboxService(db)
    service.enqueue(user=bad, kind="verification")
    service.enqueue(user=good, kind="verification")
    db.commit()
    result = service.send_pending()
    assert result == {"sent": 1, "failed": 1} and [m["to"] for m in mailbox] == ["fine@example.com"]
    parked = db.query(Notification).filter_by(recipient_user_id=bad.id).one()
    assert parked.sent_at is None and parked.metadata_json["attempts"] == 1 and parked.metadata_json["retry_after"]
    assert service.send_pending() == {"sent": 0, "failed": 0}  # backing off, not retried yet


def test_people_who_confirmed_meanwhile_are_not_emailed(db, make_user, mailbox):
    user = make_user(is_email_verified=False)
    AuthEmailOutboxService(db).enqueue(user=user, kind="verification")
    db.commit()
    user.is_email_verified = True
    db.commit()
    AuthEmailOutboxService(db).send_pending()
    assert mailbox == [] and db.query(Notification).filter_by(recipient_user_id=user.id).one().sent_at is not None


def test_resend_is_silent_about_unknown_or_confirmed_emails_and_never_queues_twice(http, db, make_user):
    client, _ = http
    waiting = make_user(email="waiting@example.com", is_email_verified=False)
    make_user(email="done@example.com", is_email_verified=True)
    answers = [client.post("/api/v1/auth/resend-verification", json={"email": e})
               for e in ("waiting@example.com", "WAITING@example.com", "done@example.com")]
    assert {a.status_code for a in answers} == {202} and len({a.json()["message"] for a in answers}) == 1
    assert client.post("/api/v1/auth/resend-verification", json={"email": "x@example.com"}).status_code == 429
    limiter.reset()
    assert client.post("/api/v1/auth/resend-verification", json={"email": "nobody@example.com"}).status_code == 202
    assert db.query(Notification).filter_by(event_type="auth.email_verification").count() == 1
    assert db.query(Notification).filter_by(recipient_user_id=waiting.id).count() == 1


def test_admin_can_email_everyone_who_never_confirmed(http, db, make_user, monkeypatch, mailbox):
    client, current = http
    current[0] = make_user(role="admin")
    old = [make_user(is_email_verified=False) for _ in range(3)]
    make_user(is_email_verified=True)
    make_user(is_email_verified=False, is_active=False)

    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(settings, "EMAIL_API_KEY", None)
    blocked = client.post("/api/v1/admin/email/verification-backfill")
    assert blocked.status_code == 409 and "EMAIL_API_KEY" in blocked.text

    monkeypatch.setattr(settings, "EMAIL_API_KEY", "re_test_key")
    monkeypatch.setattr(settings, "EMAIL_FROM_ADDRESS", "hello@tailora.ng")
    status = client.get("/api/v1/admin/email/status").json()
    assert status["ready"] is True and status["unverified_accounts"] >= 3
    queued = client.post("/api/v1/admin/email/verification-backfill")
    assert queued.status_code == 202 and queued.json()["queued"] == status["unverified_accounts"]
    AuthEmailOutboxService(db).send_pending(limit=50)
    assert {u.email for u in old} <= {m["to"] for m in mailbox}
    # Running it again doesn't double up anyone still waiting.
    again = client.post("/api/v1/admin/email/verification-backfill").json()["queued"]
    assert db.query(Notification).filter_by(event_type="auth.email_verification", sent_at=None).count() <= again


def test_send_everything_drains_past_the_old_batch_size(db, make_user, mailbox):
    service = AuthEmailOutboxService(db)
    for _ in range(25):
        service.enqueue(user=make_user(is_email_verified=False), kind="verification")
    db.commit()
    assert service.send_pending(limit=None) == {"sent": 25, "failed": 0}
    assert service.pending_count() == 0


def test_a_reset_request_sends_that_persons_email_even_behind_a_backlog(db, make_user, mailbox, monkeypatch):
    from app.services.auth_service import AuthService
    service = AuthEmailOutboxService(db)
    for _ in range(25):  # older emails waiting
        service.enqueue(user=make_user(is_email_verified=False), kind="verification")
    db.commit()
    person = make_user(email="needs-reset@example.com")
    user = AuthService(db).request_password_reset("needs-reset@example.com")
    assert user.id == person.id
    service.send_pending(user_id=user.id)
    assert [m["to"] for m in mailbox] == ["needs-reset@example.com"]
    assert "Reset your Tailora password" == mailbox[0]["subject"]


@pytest.mark.parametrize("value,ok", [
    ("hello@tailora.ng", True), ("Tailora <hello@tailora.ng>", True), ('"Tailora Support" <hello@tailora.ng>', True),
    ('"Tailora <hello@tailora.ng>"', False), ("Tailora hello@tailora.ng", False),
    ("Tailora <hello@tailora.ng", False), ("no-reply@fashionhub.example", False), ("", False),
])
def test_sender_address_format_is_checked_before_sending(value, ok):
    from app.integrations.notifications.email import sender_problem
    assert (sender_problem(value) is None) is ok


def test_pasted_quotes_and_newlines_are_cleaned_from_the_sender(monkeypatch):
    from app.core.config import Settings
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", '"Tailora <hello@tailora.ng>"\n')
    assert Settings().EMAIL_FROM_ADDRESS == "Tailora <hello@tailora.ng>"
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", '"Tailora Support" <hello@tailora.ng>')
    assert Settings().EMAIL_FROM_ADDRESS == '"Tailora Support" <hello@tailora.ng>'  # its own quotes stay


def test_resend_rejection_reason_is_kept_without_email_addresses(monkeypatch):
    import httpx
    from app.integrations.notifications import email as email_module
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(settings, "EMAIL_API_KEY", "re_test")
    monkeypatch.setattr(settings, "EMAIL_FROM_ADDRESS", "Tailora <hello@tailora.ng>")
    reply = httpx.Response(422, json={"statusCode": 422, "name": "validation_error",
                                      "message": "The tailora.ng domain is not verified. Sender hello@tailora.ng, to kemi@example.com"})
    monkeypatch.setattr(email_module.httpx, "post", lambda *a, **k: reply)
    with pytest.raises(ExternalProviderError) as caught:
        email_module.send_email(to_address="kemi@example.com", subject="s", html_body="<p>x</p>")
    message = str(caught.value)
    assert "HTTP 422" in message and "validation_error" in message and "domain is not verified" in message
    assert "@" not in message


def test_admin_sees_the_providers_last_refusal(http, db, make_user, mailbox):
    client, current = http
    current[0] = make_user(role="admin")
    AuthEmailOutboxService(db).enqueue(user=make_user(email="bounce-x@example.com", is_email_verified=False), kind="verification")
    db.commit()
    AuthEmailOutboxService(db).send_pending()
    assert "HTTP 422" in client.get("/api/v1/admin/email/status").json()["last_error"]
