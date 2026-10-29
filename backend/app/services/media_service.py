"""Private-by-default upload validation backed by the configured object store."""
from fastapi import UploadFile
from app.core.config import settings
from app.core.exceptions import ValidationAppError
from app.integrations.storage.object_storage import get_storage_provider, build_object_key
from app.utils.file_upload import MAX_UPLOAD_SIZE_BYTES, validate_upload

MIMES = {"image/jpeg": ("jpg", bytes((255,216,255))),
         "image/png": ("png", bytes((137,80,78,71,13,10,26,10))),
         "image/webp": ("webp", b"RIFF"),
         "application/pdf": ("pdf", b"%PDF-")}


async def save_media(file: UploadFile, *, owner_id, purpose: str, public: bool = False):
    if purpose not in {"product", "kyc", "kyb", "delivery", "portfolio", "design", "avatar"}:
        raise ValidationAppError("Unsupported media purpose.")
    if settings.APP_ENV in {"production", "staging"} and settings.STORAGE_PROVIDER == "local":
        raise ValidationAppError("Persistent storage is required.")
    if public and settings.STORAGE_PROVIDER not in {"local", "postgres"} and not settings.STORAGE_PUBLIC_BASE_URL:
        raise ValidationAppError("Product image public storage URL is not configured.")
    mime = (file.content_type or "").lower()
    try:
        raw = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    finally:
        await file.close()
    validate_upload(content_type=mime, size_bytes=len(raw), allow_documents=purpose in {"kyc", "kyb"})
    if not raw or mime not in MIMES:
        raise ValidationAppError("Invalid or empty file.")
    ext, signature = MIMES[mime]
    if not raw.startswith(signature) or (mime == "image/webp" and raw[8:12] != b"WEBP"):
        raise ValidationAppError("File contents do not match the MIME type.")
    key = build_object_key(folder=f"{purpose}/{owner_id}", filename=f"attachment.{ext}")
    result = get_storage_provider().upload(key=key, file_bytes=raw, content_type=mime, is_public=public)
    return {"file_url": result, "url": result, "filename": file.filename or "attachment",
            "content_type": mime, "size_bytes": len(raw), "status": "uploaded"}
