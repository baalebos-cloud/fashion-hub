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


# ---- review fixes -----------------------------------------------------------------------

def test_http_client_logs_are_kept_quiet_so_nins_in_urls_never_reach_logs():
    import logging
    from app.core.logging import configure_logging
    configure_logging()
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() >= logging.WARNING


def test_older_records_without_a_fingerprint_still_count_as_used(ctx):
    from app.core.identity_encryption import encrypt_identity
    db = ctx["db"]
    older = ctx["make_user"](role="tailor", full_name="Kemi Adeyemi", profile_photo_url=PHOTO)
    legacy = KYCVerification(user_id=older.id, id_type="nin", status="verified", id_number_encrypted=encrypt_identity(NIN))
    db.add(legacy)
    db.commit()
    body = _submit(ctx).json()
    assert body["status"] == "under_review"
    db.refresh(legacy)
    assert legacy.nin_fingerprint  # fingerprinted on the way
    record = db.query(KYCVerification).filter_by(user_id=ctx["tailor"].id).one()
    assert record.auto_checks["checks"]["nin_not_used_elsewhere"] is False


def test_an_unreadable_older_record_sends_the_check_to_review(ctx):
    db = ctx["db"]
    older = ctx["make_user"](role="tailor")
    db.add(KYCVerification(user_id=older.id, id_type="nin", status="verified", id_number_encrypted="fernet:v1:not-readable"))
    db.commit()
    assert _submit(ctx).json()["status"] == "under_review"


@pytest.mark.parametrize("mine, theirs, ok", [
    ("Kemi Kemi", "KEMI ABOSEDE ADEYEMI", False),          # one official word can't be used twice
    ("Kemi Kemi", "KEMI KEMI ADEYEMI", True),               # unless the record has it twice
    ("Ade Adeyemi", "ADEYEMI ADE", True),
    ("Kemi Abosede Adeyemi Bola", "KEMI ABOSEDE ADEYEMI", False),
])
def test_name_words_are_matched_one_to_one(mine, theirs, ok):
    assert name_matches(mine, theirs) is ok


def test_same_nin_sent_by_two_accounts_at_once_verifies_only_one(engine, monkeypatch):
    """Two submissions racing with the same NIN: the per-NIN lock makes the second wait and
    see the first, so it goes to manual review instead of a second automatic approval."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import Session
    from app.models.user import User
    from app.services.kyc_service import KYCService
    import uuid as _uuid
    monkeypatch.setattr(settings, "IDENTITY_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "NIN_AUTO_APPROVE", True)
    monkeypatch.setattr(kyc_factory, "get_nin_provider", lambda: FakeProvider())
    nin = "7" + _uuid.uuid4().int.__str__()[:10]
    with Session(engine) as s:
        users = [User(email=f"{_uuid.uuid4()}@example.com", hashed_password="x", full_name="Kemi Adeyemi",
                      role="tailor", profile_photo_url=PHOTO, is_active=True) for _ in range(2)]
        s.add_all(users)
        s.commit()
        ids = [u.id for u in users]
    barrier = Barrier(2)

    def submit(user_id):
        with Session(engine) as s:
            barrier.wait(timeout=10)
            return KYCService(s).submit(user_id=user_id, nin_number=nin, document_storage_keys=["kyc/id.jpg"],
                                        home_latitude=None, home_longitude=None,
                                        home_formatted_address="3 Allen Avenue, Ikeja", date_of_birth=date(1990, 4, 12)).status
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = sorted(f.result(timeout=30) for f in [pool.submit(submit, i) for i in ids])
        assert statuses == ["under_review", "verified"]
    finally:
        with Session(engine) as s:
            s.query(KYCVerification).filter(KYCVerification.user_id.in_(ids)).delete(synchronize_session=False)
            s.query(Notification).filter(Notification.recipient_user_id.in_(ids)).delete(synchronize_session=False)
            s.query(AuditLog).filter(AuditLog.action == "kyc.auto_approved").delete(synchronize_session=False)
            s.query(User).filter(User.id.in_(ids)).delete(synchronize_session=False)
            s.commit()
