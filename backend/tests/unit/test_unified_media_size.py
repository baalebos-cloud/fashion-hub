"""Unified media payload regression tests."""
from app.utils.file_upload import validate_upload, MAX_UPLOAD_SIZE_BYTES
from app.core.exceptions import ValidationAppError
import pytest


def test_mobile_photo_up_to_fifteen_megabytes_allowed():
    assert MAX_UPLOAD_SIZE_BYTES == 15 * 1024 * 1024
    validate_upload(content_type="image/jpeg", size_bytes=8 * 1024 * 1024)
    validate_upload(content_type="image/jpeg", size_bytes=MAX_UPLOAD_SIZE_BYTES)


def test_oversized_file_rejected():
    with pytest.raises(ValidationAppError, match="15MB"):
        validate_upload(content_type="image/jpeg", size_bytes=MAX_UPLOAD_SIZE_BYTES + 1)


def test_pdf_only_allowed_for_kyc_kyb():
    with pytest.raises(ValidationAppError):
        validate_upload(content_type="application/pdf", size_bytes=2048)
    validate_upload(content_type="application/pdf", size_bytes=2048, allow_documents=True)
