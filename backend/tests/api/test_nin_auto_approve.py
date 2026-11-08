"""Identity checks approve themselves only when every rule passes; everything else goes to an admin."""
from datetime import date
from unittest.mock import MagicMock

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ExternalProviderError, NotFoundError
from app.integrations import kyc as kyc_factory
from app.integrations.kyc.dojah import DojahNINProvider
from app.integrations.kyc.nin_provider import NINVerificationResult
from app.main import app
from app.models.audit_log import AuditLog
from app.models.kyc_verification import KYCVerification
from app.models.notification import Notification
from app.models.professional import Professional
from app.services.nin_matching import evaluate, name_matches

PHOTO = "/api/v1/media/files/profile-photo.jpg"
NIN = "70123456789"
OFFICIAL = NINVerificationResult(nin=NIN, full_name="KEMI ABOSEDE ADEYEMI", date_of_birth=date(1990, 4, 12), gender="FEMALE")


class FakeProvider:
    def __init__(self, result=OFFICIAL, error=None):
        self.result, self.error = result, error

    def verify(self, nin_number):
        if self.error:
            raise self.error
        return self.result


@pytest.fixture()
def ctx(db, make_user, monkeypatch):
    monkeypatch.setattr(settings, "IDENTITY_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "NIN_AUTO_APPROVE", True)
    monkeypatch.setattr(settings, "NIN_PROVIDER", "dojah")
    provider = FakeProvider()
    monkeypatch.setattr(kyc_factory, "get_nin_provider", lambda: provider)
    tailor = make_user(role="tailor", full_name="Kemi Adeyemi", profile_photo_url=PHOTO)
    db.add(Professional(user_id=tailor.id, professional_type="tailor", is_verified=False))
    db.commit()
    current = [tailor]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield dict(http=http, db=db, current=current, tailor=tailor, provider=provider, make_user=make_user)
    app.dependency_overrides.clear()


def _submit(ctx, dob="1990-04-12", nin=NIN):
    body = {"nin_number": nin, "document_storage_keys": ["kyc/id.jpg"], "home_formatted_address": "3 Allen Avenue, Ikeja"}
    if dob:
        body["date_of_birth"] = dob
    return ctx["http"].post("/api/v1/kyc", json=body)


def test_matching_details_are_approved_automatically(ctx):
    res = _submit(ctx)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "verified" and body["auto_approved"] is True
    assert body["nin_verified_full_name"] == "KEMI ABOSEDE ADEYEMI"
    db = ctx["db"]
    assert db.query(Professional).filter_by(user_id=ctx["tailor"].id).one().is_verified is True
    assert db.query(Notification).filter_by(recipient_user_id=ctx["tailor"].id, event_type="verification.kyc.verified").count() == 1
    audit = db.query(AuditLog).filter_by(action="kyc.auto_approved").one()
    assert audit.actor_user_id is None and all(audit.metadata_json["checks"].values())
    assert NIN not in str(audit.metadata_json)
    record = db.query(KYCVerification).filter_by(user_id=ctx["tailor"].id).one()
    assert record.reviewed_by_user_id is None and record.reviewed_at is not None
    assert record.nin_fingerprint and NIN not in record.nin_fingerprint


@pytest.mark.parametrize("dob, failed", [("1991-04-12", "date_of_birth_matches"), (None, "date_of_birth_matches")])
def test_wrong_or_missing_date_of_birth_goes_to_review(ctx, dob, failed):
    body = _submit(ctx, dob=dob).json()
    assert body["status"] == "under_review" and body["auto_approved"] is False
    record = ctx["db"].query(KYCVerification).filter_by(user_id=ctx["tailor"].id).one()
    assert record.auto_checks["checks"][failed] is False
    assert ctx["db"].query(Professional).filter_by(user_id=ctx["tailor"].id).one().is_verified is False


def test_name_that_does_not_match_goes_to_review(ctx):
    ctx["provider"].result = NINVerificationResult(nin=NIN, full_name="CHIDI OKAFOR", date_of_birth=date(1990, 4, 12), gender="MALE")
    assert _submit(ctx).json()["status"] == "under_review"


def test_same_nin_on_another_account_goes_to_review(ctx):
    assert _submit(ctx).json()["status"] == "verified"
    other = ctx["make_user"](role="tailor", full_name="Kemi Adeyemi", profile_photo_url=PHOTO)
    ctx["current"][0] = other
    body = _submit(ctx).json()
    assert body["status"] == "under_review"
    record = ctx["db"].query(KYCVerification).filter_by(user_id=other.id).one()
    assert record.auto_checks["checks"]["nin_not_used_elsewhere"] is False


def test_provider_outage_goes_to_review_and_unknown_nin_is_refused(ctx):
    ctx["provider"].error = ExternalProviderError("down")
    assert _submit(ctx).json()["status"] == "under_review"
    ctx["provider"].error = NotFoundError("NIN could not be verified.")
    ctx["current"][0] = ctx["make_user"](role="tailor", full_name="Ada Obi", profile_photo_url=PHOTO)
    assert _submit(ctx).status_code == 404


def test_switch_off_means_an_admin_always_decides(ctx, monkeypatch):
    monkeypatch.setattr(settings, "NIN_AUTO_APPROVE", False)
    body = _submit(ctx).json()
    assert body["status"] != "verified" and body["auto_approved"] is False


def test_admin_queue_shows_which_rules_failed(ctx):
    _submit(ctx, dob="1991-01-01")
    ctx["current"][0] = ctx["make_user"](role="admin")
    [item] = ctx["http"].get("/api/v1/admin/verifications", params={"kind": "kyc"}).json()
    assert item["auto_checks"]["date_of_birth_matches"] is False
    assert item["auto_checks"]["name_matches"] is True


@pytest.mark.parametrize("mine, theirs, ok", [
    ("Kemi Adeyemi", "KEMI ABOSEDE ADEYEMI", True),
    ("Adeyemi Kemi", "KEMI ABOSEDE ADEYEMI", True),        # order doesn't matter
    ("Kemi Adeyemii", "KEMI ABOSEDE ADEYEMI", True),       # one-letter typo
    ("Kemi Adebayo", "KEMI ABOSEDE ADEYEMI", False),       # different surname
    ("Kemi", "KEMI ABOSEDE ADEYEMI", False),               # one word isn't enough
    ("Oluwafemi Adé", "OLUWAFEMI ADE", True),              # accents
])
def test_name_rule(mine, theirs, ok):
    assert name_matches(mine, theirs) is ok


def test_every_rule_must_pass():
    base = dict(account_name="Kemi Adeyemi", official_name="KEMI ADEYEMI", entered_dob=date(1990, 1, 1),
                official_dob=date(1990, 1, 1), has_photo=True, duplicate=False)
    assert evaluate(**base)["passed"] is True
    for change in ({"has_photo": False}, {"duplicate": True}, {"official_name": None}, {"entered_dob": None}):
        assert evaluate(**{**base, **change})["passed"] is False


def _dojah(monkeypatch, status, payload=None):
    response = MagicMock(status_code=status)
    response.json.return_value = payload
    calls = []
    monkeypatch.setattr(httpx, "get", lambda url, **kw: calls.append((url, kw)) or response)
    return calls


def test_dojah_reads_the_documented_response(monkeypatch):
    calls = _dojah(monkeypatch, 200, {"entity": {"first_name": "John", "middle_name": "Doe", "last_name": "Musa",
                                                   "gender": "Male", "date_of_birth": "1982-01-01", "photo": "abc"}})
    result = DojahNINProvider(secret_key="sk", app_id="app", base_url="https://sandbox.dojah.io").verify(NIN)
    assert result.full_name == "John Doe Musa" and result.date_of_birth == date(1982, 1, 1) and result.gender == "MALE"
    url, kw = calls[0]
    assert url == "https://sandbox.dojah.io/api/v1/kyc/nin" and kw["params"] == {"nin": NIN}
    assert kw["headers"]["AppId"] == "app" and kw["headers"]["Authorization"] == "sk"


@pytest.mark.parametrize("status, error", [(404, NotFoundError), (401, ExternalProviderError), (402, ExternalProviderError),
                                           (424, ExternalProviderError), (429, ExternalProviderError)])
def test_dojah_errors(monkeypatch, status, error):
    _dojah(monkeypatch, status, {})
    with pytest.raises(error):
        DojahNINProvider(secret_key="sk", app_id="app").verify(NIN)


def test_dojah_needs_both_keys():
    with pytest.raises(ExternalProviderError):
        DojahNINProvider(secret_key="sk", app_id="").verify(NIN)
