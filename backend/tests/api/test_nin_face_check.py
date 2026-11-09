"""Live selfie and profile photo must both match the NIN record photo before automatic approval."""
import uuid
from datetime import date

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ExternalProviderError
from app.integrations import kyc as kyc_factory
from app.integrations.kyc import prembly_face
from app.integrations.kyc.nin_provider import NINVerificationResult
from app.integrations.kyc.prembly_face import FaceMatch, compare_face_with_nin
from app.main import app
from app.models.kyc_verification import KYCVerification
from app.models.professional import Professional
from app.models.stored_media import StoredMedia
from app.models.verification_document import VerificationDocument
from app.services.document_check_service import DocumentCheck
from app.services.kyc_service import KYCService

NIN = "70123456789"
OFFICIAL = NINVerificationResult(nin=NIN, full_name="KEMI ABOSEDE ADEYEMI", date_of_birth=date(1990, 4, 12), gender="FEMALE")
SELFIE, PROFILE = b"\xff\xd8selfie", b"\xff\xd8profile"


class Reply:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def json(self):
        return self.body


# ---- the Prembly call -----------------------------------------------------------------------------
def test_match_and_no_match(monkeypatch):
    monkeypatch.setattr(settings, "PREMBLY_API_KEY", "test")
    sent = {}

    def post(url, **kw):
        sent.update(kw)
        return Reply({"status": True, "response_code": "00", "face_data": {"status": True, "confidence": 97.4}})

    assert compare_face_with_nin(NIN, SELFIE, http_post=post) == FaceMatch(True, 97.4)
    assert sent["json"]["number"] == NIN and sent["json"]["face_confidence_threshold"] == settings.NIN_FACE_THRESHOLD
    no = compare_face_with_nin(NIN, SELFIE, http_post=lambda *a, **k: Reply(
        {"response_code": "00", "face_data": {"status": False, "confidence": 41.0}}))
    assert no == FaceMatch(False, 41.0)
    low = compare_face_with_nin(NIN, SELFIE, http_post=lambda *a, **k: Reply(
        {"response_code": "00", "face_data": {"status": True, "confidence": 0.62}}))
    assert low == FaceMatch(False, 62.0)  # 0–1 scale, below the threshold


@pytest.mark.parametrize("reply", [Reply({}, 500), Reply({"response_code": "01"}), Reply("nonsense")])
def test_no_comparison_is_an_error_not_a_mismatch(monkeypatch, reply):
    monkeypatch.setattr(settings, "PREMBLY_API_KEY", "test")
    with pytest.raises(ExternalProviderError):
        compare_face_with_nin(NIN, SELFIE, http_post=lambda *a, **k: reply)


# ---- on submission ----------------------------------------------------------------------------------
@pytest.fixture()
def ctx(db, make_user, monkeypatch):
    monkeypatch.setattr(settings, "IDENTITY_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "NIN_AUTO_APPROVE", True)
    monkeypatch.setattr(settings, "NIN_FACE_CHECK", True)
    monkeypatch.setattr(settings, "NIN_PROVIDER", "dojah")

    class Provider:
        def verify(self, nin_number):
            return OFFICIAL

    monkeypatch.setattr(kyc_factory, "get_nin_provider", lambda: Provider())
    monkeypatch.setattr(KYCService, "_check_documents", lambda self, *a, **k: DocumentCheck(
        checks={"document_readable": True}, passed=True, note="ok", provider="test"))
    tailor = make_user(role="tailor", full_name="Kemi Adeyemi")
    avatar_id = uuid.uuid4()
    db.add(StoredMedia(id=avatar_id, owner_user_id=tailor.id, storage_key=f"avatar/{tailor.id}/p.jpg",
                       content_type="image/jpeg", is_public=True, content=PROFILE))
    tailor.profile_photo_url = f"https://api.example/api/v1/media/files/{avatar_id}"
    selfie_key = f"kyc/{tailor.id}/selfie.jpg"
    db.add(StoredMedia(id=uuid.uuid4(), owner_user_id=tailor.id, storage_key=selfie_key, content_type="image/jpeg",
                       is_public=False, content=SELFIE))
    db.add(Professional(user_id=tailor.id, professional_type="tailor", is_verified=False))
    db.commit()
    results = {SELFIE: FaceMatch(True, 96.0), PROFILE: FaceMatch(True, 91.0)}

    def fake(nin, image):
        result = results[image]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(prembly_face, "compare_face_with_nin", fake)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: tailor
    with TestClient(app) as http:
        yield dict(http=http, db=db, tailor=tailor, selfie_key=selfie_key, results=results)
    app.dependency_overrides.clear()


def _submit(ctx, selfie=True):
    body = {"nin_number": NIN, "document_storage_keys": ["kyc/id.jpg"], "home_formatted_address": "3 Allen Avenue",
            "date_of_birth": "1990-04-12"}
    if selfie:
        body["selfie_storage_key"] = ctx["selfie_key"]
    return ctx["http"].post("/api/v1/kyc", json=body)


def _record(ctx):
    return ctx["db"].query(KYCVerification).filter_by(user_id=ctx["tailor"].id).one()


def test_both_faces_match_so_approved(ctx):
    res = _submit(ctx)
    assert res.status_code == 201, res.text and res.json()["status"] == "verified"
    assert res.json()["status"] == "verified"
    record = _record(ctx)
    assert record.auto_checks["checks"]["selfie_matches_nin"] is True
    assert record.auto_checks["face"] == {"selfie_confidence": 96.0, "profile_photo_confidence": 91.0}
    assert ctx["db"].query(VerificationDocument).filter_by(kyc_verification_id=record.id, document_type="selfie").count() == 1


@pytest.mark.parametrize("which, check", [(SELFIE, "selfie_matches_nin"), (PROFILE, "profile_photo_matches_nin")])
def test_a_face_that_does_not_match_goes_to_an_admin(ctx, which, check):
    ctx["results"][which] = FaceMatch(False, 38.0)
    assert _submit(ctx).json()["status"] == "under_review"
    assert _record(ctx).auto_checks["checks"][check] is False


def test_face_service_trouble_goes_to_an_admin_with_the_reason(ctx):
    ctx["results"][SELFIE] = ExternalProviderError("Face matching is temporarily unavailable.")
    assert _submit(ctx).json()["status"] == "under_review"
    face = _record(ctx).auto_checks["face"]
    assert face["selfie_problem"] == "Face matching is temporarily unavailable."


def test_a_selfie_is_required_when_face_checks_are_on(ctx):
    res = _submit(ctx, selfie=False)
    assert res.status_code == 422 and "selfie" in res.text


def test_someone_elses_upload_cant_be_used_as_the_selfie(ctx):
    ctx["selfie_key"] = f"kyc/{uuid.uuid4()}/selfie.jpg"
    res = _submit(ctx)
    assert res.status_code == 422


def test_off_by_default_changes_nothing(ctx, monkeypatch):
    monkeypatch.setattr(settings, "NIN_FACE_CHECK", False)
    assert _submit(ctx, selfie=False).json()["status"] == "verified"
    assert "selfie_matches_nin" not in _record(ctx).auto_checks["checks"]
