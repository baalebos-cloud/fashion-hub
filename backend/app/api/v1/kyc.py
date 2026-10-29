"""
/kyc

Individual identity verification. NIN is compulsory for every
professional, vendor business-owner, and delivery partner -- see
kyc_service.py::submit and docs/nin-verification.md.
"""
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.core.exceptions import ValidationAppError
from app.integrations.storage.object_storage import build_object_key, get_storage_provider
from app.utils.file_upload import validate_upload, MAX_UPLOAD_SIZE_BYTES
from app.models.user import User
from app.schemas.kyc import KYCStatusResponse, SubmitKYCRequest
from app.services.kyc_service import KYCService

router = APIRouter(prefix="/kyc", tags=["KYC"])


@router.post("", response_model=KYCStatusResponse, status_code=201)
def submit_kyc(payload: SubmitKYCRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = KYCService(db)
    return service.submit(
        user_id=current_user.id,
        nin_number=payload.nin_number,
        document_storage_keys=payload.document_storage_keys,
        home_latitude=payload.home_latitude,
        home_longitude=payload.home_longitude,
        home_formatted_address=payload.home_formatted_address,
    )


@router.get("/status", response_model=KYCStatusResponse)
def get_kyc_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.repositories.kyc_repository import KYCRepository

    verification = KYCRepository(db).get_latest_kyc_for_user(current_user.id)
    if not verification:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("No KYC submission found.")
    return verification


@router.post("/documents", status_code=201)
async def upload_kyc_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Private supporting document upload. Return an opaque storage key, never a public URL."""
    if settings.APP_ENV in {"production", "staging"} and settings.STORAGE_PROVIDER == "local":
        raise ValidationAppError("Secure document storage is not configured.")
    content_type = (file.content_type or "").lower()
    try:
        raw = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    finally:
        await file.close()
    validate_upload(content_type=content_type, size_bytes=len(raw), allow_documents=True)
    if not raw:
        raise ValidationAppError("The document is empty.")
    signatures = {
        "image/jpeg": raw.startswith(bytes.fromhex("ffd8ff")),
        "image/png": raw.startswith(bytes.fromhex("89504e470d0a1a0a")),
        "image/webp": raw.startswith(b"RIFF") and raw[8:12] == b"WEBP",
        "application/pdf": raw.startswith(b"%PDF-"),
    }
    if not signatures.get(content_type, False):
        raise ValidationAppError("Document content does not match its file type.")
    # The random object key does not contain the submitted filename or NIN.
    extension = {
        "image/jpeg": "jpg", "image/png": "png",
        "image/webp": "webp", "application/pdf": "pdf",
    }[content_type]
    key = build_object_key(folder=f"kyc/{current_user.id}", filename=f"document.{extension}")
    storage = get_storage_provider()
    stored_key = storage.upload(key=key, file_bytes=raw, content_type=content_type, is_public=False)
    return {"url": stored_key, "document_storage_key": stored_key, "file_name": file.filename or "document", "status": "uploaded"}


@router.post("/upload-id", status_code=201)
async def upload_id_alias(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Compatibility endpoint with private document keys; never exposes ID photos publicly."""
    return await upload_kyc_document(file=file, current_user=current_user)
