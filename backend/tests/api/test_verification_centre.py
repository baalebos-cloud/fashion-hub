"""Verification centre: KYB with CAC lookup, admin queue, approval effects, no stuck submissions."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ExternalProviderError, NotFoundError
from app.integrations.kyc import prembly_cac
from app.integrations.kyc.prembly_cac import CACResult
from app.main import app
from app.models.delivery_partner import DeliveryPartner
from app.models.kyb_verification import KYBVerification
from app.models.kyc_verification import KYCVerification
from app.models.notification import Notification
from app.models.professional import Professional
from app.models.vendor import Vendor
from app.services.verification_service import company_names_match, normalize_registration

PHOTO = "/api/v1/media/files/profile-photo.jpg"


@pytest.fixture(autouse=True)
def _review_window_open(monkeypatch):
    """These tests cover the review rules; the authenticator step-up is tested in test_admin_step_up.py."""
    from app.services.admin_auth_service import AdminStepUpService
    monkeypatch.setattr(AdminStepUpService, "require", lambda self, **_: None)


@pytest.fixture()
def http(db):
    current = [None]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as client:
        client.current = current
        yield client
    app.dependency_overrides.clear()


def kyb_body(number="RC 1234567", company_type="RC"):
    return {"business_registration_number": number, "company_type": company_type,
            "document_storage_keys": ["kyb/cert.pdf"]}


def test_registration_number_and_name_rules():
    assert normalize_registration("rc-1234567", "RC") == "1234567"
    assert normalize_registration("BN 0098 765", "BN") == "0098765"
    with pytest.raises(Exception):
        normalize_registration("ABC", "RC")
    assert company_names_match("Kemi Couture", "KEMI COUTURE LIMITED") is True
    assert company_names_match("Fabric Hub", "Zenith Oil and Gas Ltd") is False
    assert company_names_match(None, "X") is None


def test_vendor_kyb_uses_cac_registry_and_blocks_duplicates(db, make_user, http, monkeypatch):
    vendor = make_user(role="vendor", profile_photo_url=PHOTO)
    db.add(Vendor(user_id=vendor.id, business_name="Lace World", is_verified=False))
    db.commit()
    calls = []
    monkeypatch.setattr(prembly_cac, "lookup_cac",
                        lambda number, kind: calls.append((number, kind)) or CACResult("LACE WORLD LIMITED", "ACTIVE"))
    http.current[0] = vendor
    response = http.post("/api/v1/kyb", json=kyb_body())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pending" and body["verified_company_name"] == "LACE WORLD LIMITED"
    assert body["name_match"] is True and body["business_registration_number"] == "1234567"
    assert calls == [("1234567", "RC")]
    assert http.post("/api/v1/kyb", json=kyb_body()).status_code == 409
    assert http.get("/api/v1/kyb/status").json()["status"] == "pending"


def test_kyb_rejects_unknown_numbers_and_holds_on_outage(db, make_user, http, monkeypatch):
    tailor = make_user(role="tailor", profile_photo_url=PHOTO)
    db.add(Professional(user_id=tailor.id, professional_type="tailor", business_name="Ankara House"))
    db.commit()
    http.current[0] = tailor

    def not_found(*_):
        raise NotFoundError("no record")
    monkeypatch.setattr(prembly_cac, "lookup_cac", not_found)
    missing = http.post("/api/v1/kyb", json=kyb_body("BN 7654321", "BN"))
    assert missing.status_code == 422 and "BN 7654321" in missing.text
    assert db.query(KYBVerification).filter_by(business_owner_user_id=tailor.id).count() == 0

    def outage(*_):
        raise ExternalProviderError("down")
    monkeypatch.setattr(prembly_cac, "lookup_cac", outage)
    held = http.post("/api/v1/kyb", json=kyb_body())
    assert held.status_code == 201 and held.json()["status"] == "under_review"

    http.current[0] = make_user(role="customer")
    assert http.post("/api/v1/kyb", json=kyb_body()).status_code == 403


def test_kyc_held_during_nin_outage_reaches_the_admin_queue_and_can_be_approved(db, make_user, http, monkeypatch):
    from cryptography.fernet import Fernet
    from app.core.config import settings
    monkeypatch.setattr(settings, "IDENTITY_ENCRYPTION_KEY", Fernet.generate_key().decode())
    tailor = make_user(role="tailor", full_name="Kemi Adeyemi", profile_photo_url=PHOTO)
    db.add(Professional(user_id=tailor.id, professional_type="tailor", business_name="Kemi Couture"))
    admin = make_user(role="admin")
    db.commit()
    http.current[0] = tailor
    payload = {"nin_number": "12345678901", "document_storage_keys": ["kyc/id.jpg"],
               "home_formatted_address": "3 Allen Avenue, Ikeja"}
    submitted = http.post("/api/v1/kyc", json=payload)  # default manual NIN provider = outage path
    assert submitted.status_code == 201 and submitted.json()["status"] == "under_review"
    assert http.post("/api/v1/kyc", json=payload).status_code == 409  # no duplicate while in review

    http.current[0] = admin
    queue = http.get("/api/v1/admin/verifications?kind=kyc")
    assert queue.status_code == 200
    item = next(i for i in queue.json() if i["applicant_name"] == "Kemi Adeyemi")
    assert item["status"] == "under_review" and item["registry_checked"] is False
    assert "12345678901" not in queue.text

    assert http.post(f"/api/v1/admin/kyc/{item['id']}/review", json={"approve": False}).status_code == 422
    assert http.post(f"/api/v1/admin/kyc/{item['id']}/review", json={"approve": True}).status_code == 200
    assert db.query(Professional).filter_by(user_id=tailor.id).one().is_verified is True
    note = db.query(Notification).filter_by(recipient_user_id=tailor.id).one()
    assert note.event_type == "verification.kyc.verified"

    http.current[0] = tailor
    summary = http.get("/api/v1/verification/me").json()
    assert summary["verified"] is True and summary["steps"][0]["status"] == "verified"
    assert summary["steps"][1]["required"] is False  # KYB optional for tailors


def test_vendor_needs_identity_and_business_before_verified(db, make_user, http, monkeypatch):
    vendor, admin = make_user(role="vendor", full_name="Bisi Ola", profile_photo_url=PHOTO), make_user(role="admin")
    db.add(Vendor(user_id=vendor.id, business_name="Fabric Hub", is_verified=False))
    kyc = KYCVerification(user_id=vendor.id, id_type="nin", status="pending", identity_match=True)
    db.add(kyc)
    db.commit()
    monkeypatch.setattr(prembly_cac, "lookup_cac", lambda *_: CACResult("ZENITH OIL AND GAS LTD", None))
    http.current[0] = vendor
    assert http.get("/api/v1/verification/me").json()["next_step"].startswith("Start with Business")
    kyb_id = http.post("/api/v1/kyb", json=kyb_body()).json()
    kyb = db.query(KYBVerification).filter_by(business_owner_user_id=vendor.id).one()
    assert kyb.name_match is False

    http.current[0] = admin
    assert http.post(f"/api/v1/admin/kyc/{kyc.id}/review", json={"approve": True}).status_code == 200
    assert db.query(Vendor).filter_by(user_id=vendor.id).one().is_verified is False  # KYB still open
    flagged = http.post(f"/api/v1/admin/kyb/{kyb.id}/review", json={"approve": True})
    assert flagged.status_code == 422 and "override" in flagged.text
    ok = http.post(f"/api/v1/admin/kyb/{kyb.id}/review",
                   json={"approve": True, "reason": "Trading name of the registered company; checked certificate."})
    assert ok.status_code == 200
    assert db.query(Vendor).filter_by(user_id=vendor.id).one().is_verified is True
    assert kyb_id["status"] == "pending"


def test_rejection_tells_the_applicant_why_and_allows_resubmission(db, make_user, http, monkeypatch):
    rider, admin = make_user(role="delivery_partner", profile_photo_url=PHOTO), make_user(role="admin")
    db.add(DeliveryPartner(user_id=rider.id, is_verified=False))
    kyc = KYCVerification(user_id=rider.id, id_type="nin", status="pending")
    db.add(kyc)
    db.commit()
    http.current[0] = admin
    http.post(f"/api/v1/admin/kyc/{kyc.id}/review", json={"approve": False, "reason": "ID photo is blurry."})
    http.current[0] = rider
    summary = http.get("/api/v1/verification/me").json()
    assert summary["steps"][0]["status"] == "rejected"
    assert summary["steps"][0]["rejection_reason"] == "ID photo is blurry."
    assert summary["next_step"].startswith("Fix the item")
    assert db.query(DeliveryPartner).filter_by(user_id=rider.id).one().is_verified is False


def test_viewing_the_checklist_never_removes_an_existing_verified_badge(db, make_user, http):
    tailor = make_user(role="tailor", profile_photo_url=PHOTO)
    db.add(Professional(user_id=tailor.id, professional_type="tailor", business_name="Old Atelier", is_verified=True))
    db.commit()
    http.current[0] = tailor
    assert http.get("/api/v1/verification/me").json()["verified"] is True
    assert db.query(Professional).filter_by(user_id=tailor.id).one().is_verified is True


def test_admin_queue_is_admin_only(make_user, http):
    http.current[0] = make_user(role="vendor", profile_photo_url=PHOTO)
    assert http.get("/api/v1/admin/verifications?kind=kyb").status_code == 403


def test_cac_client_parses_prembly_and_maps_errors(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "KYB_PROVIDER", "prembly")
    monkeypatch.setattr(settings, "PREMBLY_API_KEY", "test-only")
    ok = MagicMock(status_code=200, json=lambda: {"status": True, "response_code": "00",
                                                  "data": {"company_name": "Kemi Couture Ltd", "status": "ACTIVE"}})
    result = prembly_cac.lookup_cac("1234567", "RC", http_post=lambda *a, **k: ok)
    assert result.company_name == "Kemi Couture Ltd" and result.registration_status == "ACTIVE"
    missing = MagicMock(status_code=200, json=lambda: {"status": False, "response_code": "01"})
    with pytest.raises(NotFoundError):
        prembly_cac.lookup_cac("1", "RC", http_post=lambda *a, **k: missing)
    # 02 (registry down), unknown codes, or status false without "01" must never
    # tell a real business their number doesn't exist: they go to manual review.
    for body in ({"status": False, "response_code": "02"}, {"status": True, "response_code": "99"},
                 {"status": False}, {"detail": "error"}):
        reply = MagicMock(status_code=200, json=lambda body=body: body)
        with pytest.raises(ExternalProviderError):
            prembly_cac.lookup_cac("1", "RC", http_post=lambda *a, reply=reply, **k: reply)
    for status_code in (404, 500, 401):  # 404 = wrong endpoint, never "company not found"
        with pytest.raises(ExternalProviderError):
            prembly_cac.lookup_cac("1", "RC", http_post=lambda *a, code=status_code, **k: MagicMock(status_code=code))
    monkeypatch.setattr(settings, "KYB_PROVIDER", "manual")
    with pytest.raises(ExternalProviderError):
        prembly_cac.lookup_cac("1", "RC", http_post=lambda *a, **k: ok)


@pytest.mark.parametrize("reply", [
    MagicMock(status_code=200, json=lambda: {"status": False, "response_code": "02"}),
    MagicMock(status_code=404),  # misconfigured PREMBLY_CAC_URL
])
def test_registry_outage_code_sends_kyb_to_manual_review(db, make_user, http, monkeypatch, reply):
    from app.core.config import settings
    monkeypatch.setattr(settings, "KYB_PROVIDER", "prembly")
    monkeypatch.setattr(settings, "PREMBLY_API_KEY", "test-only")
    vendor = make_user(role="vendor", profile_photo_url=PHOTO)
    db.add(Vendor(user_id=vendor.id, business_name="Lace World"))
    db.commit()
    monkeypatch.setattr(prembly_cac.httpx, "post", lambda *a, **k: reply)
    http.current[0] = vendor
    response = http.post("/api/v1/kyb", json=kyb_body())
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "under_review"


def test_riders_vendors_and_tailors_need_a_profile_photo_but_customers_do_not(http, make_user, db):
    rider, admin = make_user(role="delivery_partner"), make_user(role="admin")
    http.current[0] = rider
    blocked = http.post("/api/v1/kyc", json={"nin_number": "12345678901", "document_storage_keys": ["k"]})
    assert blocked.status_code == 422 and "profile photo" in blocked.text
    vendor = make_user(role="vendor")
    http.current[0] = vendor
    assert "profile photo" in http.post("/api/v1/kyb", json={
        "business_registration_number": "RC1234567", "company_type": "RC", "document_storage_keys": ["k"]}).text
    # Can't remove the photo once set; customers can.
    rider.profile_photo_url = PHOTO
    db.commit()
    http.current[0] = rider
    assert http.patch("/api/v1/users/me", json={"profile_photo_url": ""}).status_code == 422
    customer = make_user(role="customer", profile_photo_url=PHOTO)
    http.current[0] = customer
    assert http.patch("/api/v1/users/me", json={"profile_photo_url": ""}).json()["profile_photo_url"] is None
    # An admin can't approve someone who still has no photo.
    pending = KYCVerification(user_id=make_user(role="tailor").id, status="under_review")
    db.add(pending)
    db.commit()
    http.current[0] = admin
    refused = http.post(f"/api/v1/admin/kyc/{pending.id}/review", json={"approve": True})
    assert refused.status_code == 422 and "profile photo" in refused.text
