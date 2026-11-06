"""Admin area: owner-only email allowlist, authenticator-app sign-in, and the activity log."""
import uuid

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core import totp
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import create_access_token, password_version
from app.main import app
from app.models.activity_log import ActivityLog

OWNER = "owner-admin@example.com"
PASSWORD = "Password123"


@pytest.fixture()
def http(db, monkeypatch):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAILS", [OWNER])
    monkeypatch.setattr(settings, "IDENTITY_ENCRYPTION_KEY", Fernet.generate_key().decode())
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def owner(make_user):
    return make_user(role="admin", email=OWNER)


def _enrol(http, email=OWNER):
    start = http.post("/api/v1/auth/admin/login", json={"email": email, "password": PASSWORD})
    assert start.status_code == 200, start.text
    return start.json()


def _sign_in(http):
    """Full first sign-in: password, set up the authenticator, enter a code."""
    step = _enrol(http)
    assert step["step"] == "enroll" and step["otpauth_uri"].startswith("otpauth://totp/")
    code = totp.code_for(step["secret"])
    done = http.post("/api/v1/auth/admin/verify", json={"challenge": step["challenge"], "code": code})
    assert done.status_code == 200, done.text
    _sign_in.last_code = code
    return step["secret"], done.json()


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_owner_signs_in_with_password_and_authenticator_code(http, owner, db):
    secret, tokens = _sign_in(http)
    assert http.get("/api/v1/admin/activity", headers=_bearer(tokens["access_token"])).status_code == 200
    from app.models.activity_log import AdminCredential
    credential = db.query(AdminCredential).filter_by(user_id=owner.id).one()
    assert credential.totp_enabled_at is not None and secret not in credential.totp_secret_encrypted
    # Later sign-ins skip setup and ask only for a code; the same code can't be replayed.
    step = _enrol(http)
    assert step["step"] == "code" and "secret" not in step
    # Resend the exact code already used (recomputing it could land in the next 30 s window).
    reused = http.post("/api/v1/auth/admin/verify", json={"challenge": step["challenge"], "code": _sign_in.last_code})
    assert reused.status_code == 401
    # Refreshing keeps the admin session valid.
    refreshed = http.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200, refreshed.text
    assert http.get("/api/v1/admin/activity", headers=_bearer(refreshed.json()["access_token"])).status_code == 200


def test_wrong_code_wrong_password_and_unknown_email_all_fail_the_same_way(http, owner, make_user, db):
    make_user(role="admin", email="someone-else@example.com")
    responses = [
        http.post("/api/v1/auth/admin/login", json={"email": OWNER, "password": "wrong-password"}),
        http.post("/api/v1/auth/admin/login", json={"email": "someone-else@example.com", "password": PASSWORD}),
        http.post("/api/v1/auth/admin/login", json={"email": "nobody@example.com", "password": PASSWORD}),
    ]
    assert {r.status_code for r in responses} == {401}
    assert len({r.json()["error"]["message"] for r in responses}) == 1
    step = _enrol(http)
    assert http.post("/api/v1/auth/admin/verify",
                     json={"challenge": step["challenge"], "code": "000000" if totp.code_for(step["secret"]) != "000000" else "111111"}
                     ).status_code == 401
    failed = db.query(ActivityLog).filter_by(event="admin_sign_in_failed").all()
    assert len(failed) == 4 and {f.details.get("email") for f in failed if f.details.get("step") == "password"} == {
        OWNER, "someone-else@example.com", "nobody@example.com"}


def test_admins_cannot_use_the_normal_sign_in(http, owner):
    response = http.post("/api/v1/auth/login", json={"email": OWNER, "password": PASSWORD})
    assert response.status_code == 401 and "/admin/login" in response.text


def test_admin_tokens_without_the_second_step_or_off_the_allowlist_are_refused(http, owner, monkeypatch):
    no_mfa = create_access_token(str(owner.id), "admin", {"password_version": password_version(owner.hashed_password)})
    assert http.get("/api/v1/admin/activity", headers=_bearer(no_mfa)).status_code == 401
    _, tokens = _sign_in(http)
    monkeypatch.setattr(settings, "ADMIN_EMAILS", ["new-owner@example.com"])
    assert http.get("/api/v1/admin/activity", headers=_bearer(tokens["access_token"])).status_code == 401
    assert http.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_production_with_no_allowlist_lets_nobody_in(http, owner, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_EMAILS", [])
    monkeypatch.setattr(settings, "APP_ENV", "production")
    assert http.post("/api/v1/auth/admin/login", json={"email": OWNER, "password": PASSWORD}).status_code == 401


def test_sign_ins_and_changes_are_logged_with_ip_and_device(http, make_user, db, monkeypatch):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    customer = make_user(email=f"{uuid.uuid4().hex[:8]}@example.com")
    device = "dev-" + uuid.uuid4().hex
    # A client can prepend fake hops; the proxy's own (last) hop is what counts.
    headers = {"X-Device-Id": device, "X-Forwarded-For": "6.6.6.6, 102.89.4.20", "User-Agent": "Mozilla/5.0 (iPhone)"}
    assert http.post("/api/v1/auth/login", json={"email": customer.email, "password": "nope"}, headers=headers).status_code == 401
    login = http.post("/api/v1/auth/login", json={"email": customer.email, "password": PASSWORD}, headers=headers)
    assert login.status_code == 200
    token = login.json()["access_token"]
    http.post("/api/v1/addresses", headers={**headers, **_bearer(token)}, json={
        "label": "Home", "recipient_name": "Ada Obi", "recipient_phone": "08031234567",
        "formatted_address": "14 Admiralty Way", "city": "Lekki", "state_region": "Lagos",
        "latitude": 6.45, "longitude": 3.47})

    entries = db.query(ActivityLog).filter(ActivityLog.device_id == device).order_by(ActivityLog.created_at).all()
    assert [e.event for e in entries] == ["sign_in_failed", "sign_in", "request"]
    assert {e.ip_address for e in entries} == {"102.89.4.20"}
    assert entries[0].details == {"email": customer.email} and entries[0].user_id is None
    assert entries[1].user_id == customer.id and entries[1].user_agent == "Mozilla/5.0 (iPhone)"
    assert entries[2].user_id == customer.id and entries[2].path == "/api/v1/addresses" and entries[2].status_code == 201
    for entry in entries:
        assert PASSWORD not in str(entry.details) and "nope" not in str(entry.details)


def test_admin_sees_activity_summary_and_a_persons_footprint(http, owner, make_user, db):
    customer = make_user()
    for ip in ("102.89.4.20", "197.210.1.5"):
        db.add(ActivityLog(user_id=customer.id, role="customer", event="sign_in", ip_address=ip, device_id="dev-abc12345"))
    db.add(ActivityLog(event="sign_in_failed", ip_address="6.6.6.6", details={"email": customer.email}))
    db.commit()
    _, tokens = _sign_in(http)
    auth = _bearer(tokens["access_token"])

    rows = http.get(f"/api/v1/admin/activity?email={customer.email}", headers=auth).json()
    assert {r["event"] for r in rows} == {"sign_in", "sign_in_failed"}
    assert all(r["user_email"] in (customer.email, None) for r in rows)
    summary = http.get("/api/v1/admin/activity/summary", headers=auth).json()
    assert summary["failed_sign_ins_24h"] >= 1 and summary["admin_sign_ins_24h"] >= 1
    assert {"ip_address": "6.6.6.6", "attempts": 1} in summary["top_failed_ips"]
    footprint = http.get(f"/api/v1/admin/users/{customer.id}/footprint", headers=auth).json()
    assert {ip["value"] for ip in footprint["ips"]} == {"102.89.4.20", "197.210.1.5"}
    assert footprint["devices"][0]["value"] == "dev-abc12345" and footprint["devices"][0]["events"] == 2


def test_admin_audit_log_lists_actions_with_actor(http, owner, db):
    from app.models.audit_log import AuditLog
    db.add(AuditLog(actor_user_id=owner.id, action="kyc.approved", resource_type="verification", ip_address="102.89.4.20"))
    db.commit()
    _, tokens = _sign_in(http)
    rows = http.get("/api/v1/admin/audit-logs", headers=_bearer(tokens["access_token"])).json()
    assert rows[0]["action"] == "kyc.approved" and rows[0]["actor_email"] == OWNER and rows[0]["ip_address"] == "102.89.4.20"


def test_admin_emails_read_as_a_plain_comma_list_from_the_environment(monkeypatch):
    from app.core.config import Settings
    monkeypatch.setenv("ADMIN_EMAILS", "Owner@Example.com, second@example.com")
    assert Settings().ADMIN_EMAILS == ["owner@example.com", "second@example.com"]


def test_browsers_may_send_the_device_id_header_cross_origin(http):
    origin = settings.CORS_ALLOWED_ORIGINS[0]
    preflight = http.options("/api/v1/auth/login", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-device-id"})
    assert preflight.status_code == 200
    assert "x-device-id" in preflight.headers["access-control-allow-headers"].lower()


def test_resetting_the_authenticator_ends_open_admin_sessions_immediately(http, owner, db):
    from app.models.activity_log import AdminCredential
    _, tokens = _sign_in(http)
    auth = _bearer(tokens["access_token"])
    assert http.get("/api/v1/admin/activity", headers=auth).status_code == 200
    # What `create_admin.py --reset-2fa` does after a lost phone.
    db.query(AdminCredential).filter_by(user_id=owner.id).delete()
    db.commit()
    assert http.get("/api/v1/admin/activity", headers=auth).status_code == 401
    assert http.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    # A token naming no credential never matches an admin without one either.
    forged = create_access_token(str(owner.id), "admin", {"password_version": password_version(owner.hashed_password), "mfa": True})
    assert http.get("/api/v1/admin/activity", headers=_bearer(forged)).status_code == 401


def test_password_resets_are_logged_against_the_account(http, make_user, db):
    from app.core.security import create_password_reset_token
    customer = make_user()
    token = create_password_reset_token(str(customer.id), customer.hashed_password)
    assert http.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "Another-Pass-123"}).status_code == 204
    entry = db.query(ActivityLog).filter_by(event="password_reset", user_id=customer.id).one()
    assert entry.role == "customer"
