"""Business (CAC) checks approved without an admin when every rule passes; anything else goes to an
admin with the failed rules listed. Nothing personal from the CAC record is stored."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.integrations.kyc import prembly_cac
from app.integrations.kyc.prembly_cac import CACPerson, CACResult, lookup_cac
from app.main import app
from app.models.audit_log import AuditLog
from app.models.kyb_verification import KYBVerification
from app.models.kyc_verification import KYCVerification
from app.models.notification import Notification
from app.models.vendor import Vendor
from app.services.kyb_matching import company_active, owner_listed

PHOTO = "/api/v1/media/files/profile-photo.jpg"
DOB = date(1990, 5, 17)
ADA = CACPerson(full_name="ADA CHIOMA OBI", date_of_birth=DOB, role="DIRECTOR", active=True)


@pytest.fixture()
def http(db, monkeypatch):
    monkeypatch.setattr(settings, "KYB_AUTO_APPROVE", True)
    current = [None]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as client:
        client.current = current
        yield client
    app.dependency_overrides.clear()


def _vendor(db, make_user, *, kyc=True, photo=True, name="Ada Obi", business="Lace World"):
    user = make_user(role="vendor", full_name=name, profile_photo_url=PHOTO if photo else None)
    db.add(Vendor(user_id=user.id, business_name=business, is_verified=False))
    if kyc:
        db.add(KYCVerification(user_id=user.id, id_type="nin", status="verified", provider="prembly",
                               nin_verified_full_name="OBI ADA CHIOMA", nin_verified_date_of_birth=DOB))
    db.commit()
    return user


def _registry(monkeypatch, *, status="ACTIVE", people=(ADA,), name="LACE WORLD LIMITED"):
    monkeypatch.setattr(prembly_cac, "lookup_cac", lambda *_: CACResult(name, status, list(people)))


def _submit(http, number="RC 1234567"):
    return http.post("/api/v1/kyb", json={"business_registration_number": number, "company_type": "RC",
                                          "document_storage_keys": ["kyb/cert.pdf"]})


def test_everything_matches_so_the_business_is_verified(db, make_user, http, monkeypatch):
    user = _vendor(db, make_user)
    _registry(monkeypatch)
    http.current[0] = user
    res = _submit(http)
    assert res.status_code == 201, res.text
    assert res.json()["status"] == "verified"
    record = db.query(KYBVerification).filter_by(business_owner_user_id=user.id).one()
    assert record.auto_checks["passed"] is True and record.reviewed_at is not None
    assert db.query(Vendor).filter_by(user_id=user.id).one().is_verified is True  # KYC + KYB done
    assert db.query(Notification).filter_by(recipient_user_id=user.id, event_type="verification.kyb.verified").count() == 1
    audit = db.query(AuditLog).filter_by(action="kyb.auto_approved", resource_id=record.id).one()
    assert "ADA" not in str(audit.metadata_json) and "1990" not in str(record.auto_checks)  # no personal data kept


@pytest.mark.parametrize("change, failed", [
    (dict(status="INACTIVE"), "company_active"),
    (dict(name="ZENITH OIL AND GAS LTD"), "business_name_matches"),
    (dict(people=(CACPerson("TUNDE BAKARE", None, "DIRECTOR", True),)), "owner_listed"),
    (dict(people=(CACPerson("ADA CHIOMA OBI", date(1991, 1, 1), "DIRECTOR", True),)), "owner_listed"),
    (dict(people=(CACPerson("ADA CHIOMA OBI", DOB, "SECRETARY", True),)), "owner_listed"),
    (dict(people=(CACPerson("ADA CHIOMA OBI", DOB, "DIRECTOR", False),)), "owner_listed"),
])
def test_any_failed_rule_goes_to_an_admin(db, make_user, http, monkeypatch, change, failed):
    user = _vendor(db, make_user)
    _registry(monkeypatch, **change)
    http.current[0] = user
    assert _submit(http).json()["status"] == "under_review"
    record = db.query(KYBVerification).filter_by(business_owner_user_id=user.id).one()
    assert record.auto_checks["checks"][failed] is False and record.auto_checks["passed"] is False
    assert db.query(Vendor).filter_by(user_id=user.id).one().is_verified is False


def test_identity_must_be_verified_first(db, make_user, http, monkeypatch):
    user = _vendor(db, make_user, kyc=False)
    _registry(monkeypatch)
    http.current[0] = user
    assert _submit(http).json()["status"] == "under_review"
    checks = db.query(KYBVerification).filter_by(business_owner_user_id=user.id).one().auto_checks["checks"]
    assert checks["identity_verified"] is False and checks["owner_listed"] is False


def test_a_registration_already_used_by_another_account_goes_to_an_admin(db, make_user, http, monkeypatch):
    first, second = _vendor(db, make_user), _vendor(db, make_user)
    _registry(monkeypatch)
    http.current[0] = first
    assert _submit(http).json()["status"] == "verified"
    http.current[0] = second
    assert _submit(http, "rc-1234567").json()["status"] == "under_review"
    checks = db.query(KYBVerification).filter_by(business_owner_user_id=second.id).one().auto_checks["checks"]
    assert checks["registration_not_used_elsewhere"] is False


def test_switched_off_keeps_the_admin_review(db, make_user, http, monkeypatch):
    monkeypatch.setattr(settings, "KYB_AUTO_APPROVE", False)
    user = _vendor(db, make_user)
    _registry(monkeypatch)
    http.current[0] = user
    assert _submit(http).json()["status"] == "pending"


def test_admins_see_which_rules_failed(db, make_user, http, monkeypatch):
    user = _vendor(db, make_user)
    _registry(monkeypatch, status="INACTIVE")
    http.current[0] = user
    _submit(http)
    from app.services.verification_service import VerificationService
    item = next(i for i in VerificationService(db).admin_queue("kyb") if i["applicant_name"] == user.full_name)
    assert item["auto_checks"]["company_active"] is False and item["auto_checks"]["owner_listed"] is True


def test_reading_people_from_the_cac_advance_reply(monkeypatch):
    monkeypatch.setattr(settings, "KYB_PROVIDER", "prembly")
    monkeypatch.setattr(settings, "PREMBLY_API_KEY", "test-key")
    reply = {"status": True, "response_code": "00", "data": {
        "company_name": "LACE WORLD LIMITED", "company_status": "ACTIVE", "directors": [
            {"firstname": "ADA", "otherName": "CHIOMA", "surname": "OBI", "dateOfBirth": "1990-05-17",
             "status": "ACTIVE", "affiliateTypeFk": {"name": "DIRECTOR"}, "isCorporate": False},
            {"firstname": "", "surname": "", "corporationName": "HOLDCO LTD", "isCorporate": True},
            {"firstname": "BOLA", "surname": "ADE", "dateOfBirth": "17/05/1985", "status": "INACTIVE",
             "affiliateTypeFk": {"name": "SECRETARY"}}]}}

    class Reply:
        status_code = 200

        def json(self):
            return reply

    result = lookup_cac("1234567", "RC", http_post=lambda *a, **k: Reply())
    assert result.registration_status == "ACTIVE" and len(result.people) == 2
    assert result.people[0] == CACPerson("ADA CHIOMA OBI", DOB, "DIRECTOR", True)
    assert result.people[1].date_of_birth == date(1985, 5, 17) and result.people[1].active is False


def test_matching_rules():
    assert company_active("ACTIVE") and company_active("Active") and not company_active("INACTIVE")
    assert not company_active(None) and not company_active("STRUCK OFF")
    assert owner_listed([ADA], verified_name="Obi Ada Chioma", verified_dob=DOB)
    assert owner_listed([CACPerson("ADA OBI", None, None, True)], verified_name="OBI ADA CHIOMA", verified_dob=DOB)
    assert not owner_listed([ADA], verified_name=None, verified_dob=None)
