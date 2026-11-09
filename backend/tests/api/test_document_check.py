"""Tailora reads the uploaded ID document; it approves only together with a matching NIN record,
writes a note for the reviewer, and keeps no ID number."""
import json
import logging
import uuid
from datetime import date

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.integrations import kyc as kyc_factory
from app.integrations.kyc.nin_provider import NINVerificationResult
from app.main import app
from app.models.kyc_verification import KYCVerification
from app.models.professional import Professional
from app.models.stored_media import StoredMedia
from app.services import document_check_service as dcs
from app.services.document_check_service import DocumentCheckService, DocumentReading, compare

PHOTO = "/api/v1/media/files/profile-photo.jpg"
NIN = "70123456789"
DOB = date(1990, 4, 12)
OFFICIAL = NINVerificationResult(nin=NIN, full_name="KEMI ABOSEDE ADEYEMI", date_of_birth=DOB, gender="FEMALE")
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64
GOOD = {"is_identity_document": True, "document_type": "NIN slip", "full_name": "ADEYEMI KEMI ABOSEDE",
        "date_of_birth": "1990-04-12", "id_number": NIN, "expiry_date": None, "legible": True,
        "signs_of_editing": False, "notes": "Clear photo."}


def reading(**change):
    return DocumentReading(**{**GOOD, **change})


# ---- the rules ------------------------------------------------------------------------------
def test_a_matching_nin_slip_passes_with_a_friendly_note():
    result = compare(reading(), account_name="Kemi Adeyemi", reference_dob=DOB, entered_nin=NIN)
    assert result.passed and all(v is not False for v in result.checks.values())
    assert "name matches" in result.note and NIN not in result.note


@pytest.mark.parametrize("change, rule, words", [
    (dict(full_name="TUNDE BAKARE"), "document_name_matches", "doesn't match the name"),
    (dict(date_of_birth="1991-01-01"), "document_date_of_birth_matches", "date of birth"),
    (dict(id_number="70123456780"), "document_nin_matches", "NIN on the document"),
    (dict(expiry_date="2020-01-01"), "document_not_expired", "expired"),
    (dict(signs_of_editing=True), "document_not_edited", "edited"),
])
def test_each_problem_fails_and_is_explained(change, rule, words):
    result = compare(reading(**change), account_name="Kemi Adeyemi", reference_dob=DOB, entered_nin=NIN)
    assert not result.passed and result.checks[rule] is False and words in result.note
    assert NIN not in result.note


@pytest.mark.parametrize("number", [None, "7012345678", "7012345678X"])
def test_a_nin_slip_must_show_the_whole_nin(number):
    for kind in ("NIN slip", "National ID card"):
        result = compare(reading(document_type=kind, id_number=number), account_name="Kemi Adeyemi",
                         reference_dob=DOB, entered_nin=NIN)
        assert result.checks["document_nin_matches"] is False and not result.passed


def test_a_slow_reader_gives_up_in_time(monkeypatch):
    import time
    monkeypatch.setattr(settings, "VERTEX_AI_ENABLED", True)
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    monkeypatch.setattr(dcs, "READ_TIMEOUT_SECONDS", 0.2)

    class SlowVertex:
        def _structured(self, schema, parts):
            time.sleep(10)

    started = time.monotonic()
    result = DocumentCheckService(vertex=SlowVertex()).check([(JPEG, "image/jpeg")], account_name="Kemi Adeyemi",
                                                            reference_dob=DOB, entered_nin=NIN)
    # Gives up long before the slow reader would finish (loading the AI library takes a moment on CI).
    assert time.monotonic() - started < 6 and not result.passed


def test_unreadable_or_not_an_id_asks_for_a_clear_photo():
    for change in (dict(legible=False), dict(is_identity_document=False)):
        result = compare(reading(**change), account_name="Kemi Adeyemi", reference_dob=DOB, entered_nin=NIN)
        assert not result.passed and "clear" in result.note


def test_a_passport_has_no_nin_to_compare():
    result = compare(reading(document_type="International passport", id_number="A12345678", expiry_date="2031-01-01"),
                     account_name="Kemi Adeyemi", reference_dob=DOB, entered_nin=NIN, today=date(2026, 11, 9))
    assert result.passed and result.checks["document_nin_matches"] is None


# ---- reading with the AI provider -------------------------------------------------------------
class Reply:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def json(self):
        return self.body


def test_reads_with_groq_and_never_logs_the_reading(monkeypatch):
    logged = []
    handler = logging.Handler()
    handler.emit = lambda record: logged.append(record.getMessage())
    logging.getLogger().addHandler(handler)
    monkeypatch.setattr(settings, "VERTEX_AI_ENABLED", False)
    monkeypatch.setattr(settings, "AI_FALLBACK_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test")
    sent = {}

    def post(url, **kwargs):
        sent.update(kwargs)
        return Reply({"choices": [{"message": {"content": json.dumps(GOOD)}}]})

    result = DocumentCheckService(http_post=post).check([(JPEG, "image/jpeg")], account_name="Kemi Adeyemi",
                                                        reference_dob=DOB, entered_nin=NIN)
    assert result.passed and result.provider == "groq"
    assert sent["json"]["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    logging.getLogger().removeHandler(handler)
    assert not any(NIN in m or "KEMI" in m for m in logged)


def test_provider_trouble_or_switched_off_never_passes(monkeypatch):
    monkeypatch.setattr(settings, "VERTEX_AI_ENABLED", False)
    monkeypatch.setattr(settings, "AI_FALLBACK_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test")
    down = DocumentCheckService(http_post=lambda *a, **k: Reply({}, 503)).check(
        [(JPEG, "image/jpeg")], account_name="Kemi Adeyemi", reference_dob=DOB, entered_nin=NIN)
    assert not down.passed and "couldn't check" in down.note
    monkeypatch.setattr(settings, "DOCUMENT_AI_CHECK", False)
    off = DocumentCheckService().check([(JPEG, "image/jpeg")], account_name="x y", reference_dob=None, entered_nin=None)
    assert not off.passed and "switched on" in off.note


# ---- on submission ------------------------------------------------------------------------------
@pytest.fixture()
def ctx(db, make_user, monkeypatch):
    monkeypatch.setattr(settings, "IDENTITY_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "NIN_AUTO_APPROVE", True)
    monkeypatch.setattr(settings, "NIN_PROVIDER", "dojah")
    monkeypatch.setattr(settings, "VERTEX_AI_ENABLED", False)
    monkeypatch.setattr(settings, "AI_FALLBACK_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test")

    class Provider:
        def verify(self, nin_number):
            return OFFICIAL

    monkeypatch.setattr(kyc_factory, "get_nin_provider", lambda: Provider())
    tailor = make_user(role="tailor", full_name="Kemi Adeyemi", profile_photo_url=PHOTO)
    db.add(Professional(user_id=tailor.id, professional_type="tailor", is_verified=False))
    key = f"kyc/{tailor.id}/id.jpg"
    db.add(StoredMedia(id=uuid.uuid4(), owner_user_id=tailor.id, storage_key=key, content_type="image/jpeg", is_public=False, content=JPEG))
    db.commit()
    readings = {"value": GOOD}
    monkeypatch.setattr(dcs.httpx, "post", lambda *a, **k: Reply(
        {"choices": [{"message": {"content": json.dumps(readings["value"])}}]}))
    current = [tailor]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield dict(http=http, db=db, tailor=tailor, key=key, readings=readings, current=current, make_user=make_user)
    app.dependency_overrides.clear()


def _submit(ctx):
    return ctx["http"].post("/api/v1/kyc", json={"nin_number": NIN, "document_storage_keys": [ctx["key"]],
                                                 "home_formatted_address": "3 Allen Avenue", "date_of_birth": "1990-04-12"})


def test_document_and_nin_record_both_match_so_approved(ctx):
    res = _submit(ctx)
    assert res.status_code == 201, res.text and res.json()["status"] == "verified"
    assert res.json()["status"] == "verified"
    record = ctx["db"].query(KYCVerification).filter_by(user_id=ctx["tailor"].id).one()
    assert record.auto_checks["checks"]["document_name_matches"] is True
    assert "Tailora checked your NIN slip" in record.auto_checks["document_note"]
    assert NIN not in json.dumps(record.auto_checks)


def test_a_document_problem_goes_to_an_admin_with_the_note(ctx):
    ctx["readings"]["value"] = {**GOOD, "full_name": "TUNDE BAKARE"}
    assert _submit(ctx).json()["status"] == "under_review"
    from app.services.verification_service import VerificationService
    item = next(i for i in VerificationService(ctx["db"]).admin_queue("kyc") if i["applicant_name"] == "Kemi Adeyemi")
    assert item["auto_checks"]["document_name_matches"] is False
    assert "TUNDE BAKARE" in item["document_note"]


def test_admin_can_run_the_check_on_an_older_submission(ctx):
    db = ctx["db"]
    from app.core.identity_encryption import encrypt_identity
    record = KYCVerification(user_id=ctx["tailor"].id, id_type="nin", status="under_review", provider="manual",
                             id_number_encrypted=encrypt_identity(NIN))
    db.add(record)
    db.flush()
    from app.models.verification_document import VerificationDocument
    db.add(VerificationDocument(kyc_verification_id=record.id, document_type="nin", storage_key=ctx["key"]))
    db.commit()
    ctx["current"][0] = ctx["make_user"](role="admin")
    res = ctx["http"].post(f"/api/v1/admin/kyc/{record.id}/document-check")
    assert res.status_code == 200, res.text
    assert res.json()["passed"] is True and "name matches" in res.json()["document_note"]
    db.refresh(record)
    assert record.status == "under_review"  # a check never decides on its own
    assert ctx["http"].post(f"/api/v1/admin/kyc/{record.id}/document-check").status_code == 200
    ctx["current"][0] = ctx["tailor"]
    assert ctx["http"].post(f"/api/v1/admin/kyc/{record.id}/document-check").status_code == 403


def test_admins_can_open_documents_from_any_storage(ctx, monkeypatch):
    db = ctx["db"]
    record = KYCVerification(user_id=ctx["tailor"].id, id_type="nin", status="under_review", provider="manual")
    db.add(record)
    db.flush()
    from app.models.verification_document import VerificationDocument
    doc = VerificationDocument(kyc_verification_id=record.id, document_type="nin", storage_key="kyc/elsewhere/id.png")
    db.add(doc)
    db.commit()
    ctx["current"][0] = ctx["make_user"](role="admin")

    class S3:
        def read(self, key):
            assert key == "kyc/elsewhere/id.png"
            return b"\x89PNG....", "image/png"

    from app.integrations.storage import object_storage
    monkeypatch.setattr(object_storage, "get_storage_provider", lambda: S3())
    res = ctx["http"].get(f"/api/v1/admin/verification-documents/{doc.id}/content")
    assert res.status_code == 200 and res.headers["content-type"] == "image/png"

    class Gone:
        def read(self, key):
            from app.core.exceptions import ExternalProviderError
            raise ExternalProviderError("missing")

    monkeypatch.setattr(object_storage, "get_storage_provider", lambda: Gone())
    res = ctx["http"].get(f"/api/v1/admin/verification-documents/{doc.id}/content")
    assert res.status_code == 404 and "upload it again" in res.text


# ---- saying why a check couldn't run, and reading PDFs ---------------------------------------------
def _groq_only(monkeypatch):
    monkeypatch.setattr(settings, "VERTEX_AI_ENABLED", False)
    monkeypatch.setattr(settings, "AI_FALLBACK_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test")


@pytest.mark.parametrize("status, body, words", [
    (401, {"error": {"code": "invalid_api_key"}}, "API key was refused"),
    (404, {"error": {"code": "model_not_found"}}, "wasn't found"),
    (429, {}, "too many requests"),
])
def test_the_note_says_exactly_why_groq_failed(monkeypatch, status, body, words):
    _groq_only(monkeypatch)
    result = DocumentCheckService(http_post=lambda *a, **k: Reply(body, status)).check(
        [(JPEG, "image/jpeg")], account_name="Kemi Adeyemi", reference_dob=DOB, entered_nin=NIN)
    assert not result.passed and not result.checked
    assert f"HTTP {status}" in result.note and words in result.note


def test_vertex_failure_is_named_before_falling_back(monkeypatch):
    monkeypatch.setattr(settings, "VERTEX_AI_ENABLED", True)
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)

    class Broken:
        def _structured(self, schema, parts):
            raise PermissionError("no access")

    result = DocumentCheckService(vertex=Broken()).check([(JPEG, "image/jpeg")], account_name="Kemi Adeyemi",
                                                        reference_dob=DOB, entered_nin=NIN)
    assert "Vertex AI: PermissionError" in result.note and not result.checked


def _pdf_with_a_page() -> bytes:
    import io

    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument.new()
    pdf.new_page(300, 200)
    out = io.BytesIO()
    pdf.save(out)
    return out.getvalue()


def test_a_pdf_nin_slip_is_sent_to_groq_as_an_image(monkeypatch):
    _groq_only(monkeypatch)
    sent = {}

    def post(url, **kwargs):
        sent.update(kwargs)
        return Reply({"choices": [{"message": {"content": json.dumps(GOOD)}}]})

    result = DocumentCheckService(http_post=post).check([(_pdf_with_a_page(), "application/pdf")],
                                                        account_name="Kemi Adeyemi", reference_dob=DOB, entered_nin=NIN)
    assert result.passed and result.checked
    assert sent["json"]["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_a_damaged_pdf_is_explained(monkeypatch):
    _groq_only(monkeypatch)
    result = DocumentCheckService(http_post=lambda *a, **k: Reply({}, 500)).check(
        [(b"%PDF-1.4 not really", "application/pdf")], account_name="Kemi Adeyemi", reference_dob=DOB, entered_nin=NIN)
    assert "couldn't be turned into an image" in result.note and not result.checked
