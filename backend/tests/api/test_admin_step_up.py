"""Approving or rejecting a verification needs a recent authenticator code."""
from datetime import datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core import totp
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.core.security import _create_token
from app.main import app
from app.models.activity_log import AdminCredential
from app.models.kyc_verification import KYCVerification
from app.services.admin_auth_service import _seal

PHOTO = "/api/v1/media/files/profile-photo.jpg"


@pytest.fixture()
def ctx(db, make_user, monkeypatch):
    limiter.reset()
    monkeypatch.setattr(settings, "IDENTITY_ENCRYPTION_KEY", Fernet.generate_key().decode())
    admin = make_user(role="admin")
    secret = totp.new_secret()
    credential = AdminCredential(user_id=admin.id, totp_secret_encrypted=_seal(secret), totp_enabled_at=datetime.utcnow())
    tailor = make_user(role="tailor", profile_photo_url=PHOTO)
    kyc = KYCVerification(user_id=tailor.id, id_type="nin", status="under_review")
    db.add_all([credential, kyc])
    db.commit()
    current = [admin]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield dict(http=http, current=current, admin=admin, secret=secret, kyc=kyc, credential=credential, db=db, make_user=make_user)
    app.dependency_overrides.clear()


def _review(ctx, token=None, approve=False):
    headers = {"X-Admin-Step-Up": token} if token else {}
    return ctx["http"].post(f"/api/v1/admin/kyc/{ctx['kyc'].id}/review", headers=headers,
                            json={"approve": approve, "reason": "Blurry photo."})


def test_review_is_refused_without_a_recent_code(ctx):
    res = _review(ctx)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "step_up_required"
    assert ctx["db"].get(KYCVerification, ctx["kyc"].id).status == "under_review"


def test_a_fresh_code_opens_a_window_for_several_decisions(ctx):
    opened = ctx["http"].post("/api/v1/admin/step-up", json={"code": totp.code_for(ctx["secret"])})
    assert opened.status_code == 200, opened.text
    body = opened.json()
    assert body["minutes"] == 5 and body["step_up_token"]
    assert _review(ctx, body["step_up_token"]).status_code == 200
    # The same window covers the next decision too.
    second = KYCVerification(user_id=ctx["make_user"](role="tailor", profile_photo_url=PHOTO).id, id_type="nin", status="pending")
    ctx["db"].add(second)
    ctx["db"].commit()
    res = ctx["http"].post(f"/api/v1/admin/kyc/{second.id}/review", headers={"X-Admin-Step-Up": body["step_up_token"]},
                           json={"approve": False, "reason": "Name doesn't match."})
    assert res.status_code == 200, res.text


def test_wrong_or_reused_codes_are_refused(ctx):
    http = ctx["http"]
    assert http.post("/api/v1/admin/step-up", json={"code": "000000" if totp.code_for(ctx["secret"]) != "000000" else "111111"}).status_code == 403
    code = totp.code_for(ctx["secret"])
    assert http.post("/api/v1/admin/step-up", json={"code": code}).status_code == 200
    replay = http.post("/api/v1/admin/step-up", json={"code": code})
    assert replay.status_code == 403 and replay.json()["error"]["code"] == "step_up_failed"
    assert http.post("/api/v1/admin/step-up", json={"code": "12ab56"}).status_code == 422


def test_pass_is_bound_to_the_admin_and_their_current_authenticator(ctx):
    token = ctx["http"].post("/api/v1/admin/step-up", json={"code": totp.code_for(ctx["secret"])}).json()["step_up_token"]
    # Expired pass.
    expired = _create_token(str(ctx["admin"].id), timedelta(seconds=-1), "admin_step_up", {"cred": str(ctx["credential"].id)})
    assert _review(ctx, expired).status_code == 403
    # Another admin can't use it.
    other = ctx["make_user"](role="admin")
    ctx["current"][0] = other
    assert _review(ctx, token).status_code == 403
    ctx["current"][0] = ctx["admin"]
    # An ordinary access-type token isn't a pass.
    access_like = _create_token(str(ctx["admin"].id), timedelta(minutes=5), "access", {"cred": str(ctx["credential"].id)})
    assert _review(ctx, access_like).status_code == 403
    # Resetting the authenticator ends the window.
    ctx["db"].delete(ctx["credential"])
    ctx["db"].commit()
    assert _review(ctx, token).status_code == 403


def test_admin_without_an_authenticator_cannot_open_a_window(ctx, make_user):
    ctx["current"][0] = make_user(role="admin")
    res = ctx["http"].post("/api/v1/admin/step-up", json={"code": "123456"})
    assert res.status_code == 403 and res.json()["error"]["code"] == "step_up_unavailable"


def test_non_admins_cannot_open_a_window(ctx, make_user):
    ctx["current"][0] = make_user(role="vendor")
    assert ctx["http"].post("/api/v1/admin/step-up", json={"code": "123456"}).status_code == 403


def test_browsers_on_another_origin_may_send_the_step_up_header(ctx):
    origin = (settings.CORS_ALLOWED_ORIGINS or ["http://localhost:5173"])[0]
    res = ctx["http"].options(f"/api/v1/admin/kyc/{ctx['kyc'].id}/review", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type,x-admin-step-up"})
    assert res.status_code == 200, res.text
    assert "x-admin-step-up" in res.headers["access-control-allow-headers"].lower()
