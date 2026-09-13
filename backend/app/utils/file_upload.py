"""Upload validation helpers: size/type allow-lists to prevent malicious or
oversized uploads before they ever reach StorageProvider."""
from app.core.exceptions import ValidationAppError

ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_DOCUMENT_CONTENT_TYPES = ALLOWED_IMAGE_CONTENT_TYPES | {"application/pdf"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def validate_upload(*, content_type: str, size_bytes: int, allow_documents: bool = False) -> None:
    allowed = ALLOWED_DOCUMENT_CONTENT_TYPES if allow_documents else ALLOWED_IMAGE_CONTENT_TYPES
    if content_type not in allowed:
        raise ValidationAppError(f"Unsupported file type '{content_type}'.")
    if size_bytes > MAX_UPLOAD_SIZE_BYTES:
        raise ValidationAppError("File exceeds the maximum allowed size of 10MB.")
