"""Regression coverage for tailor-only retry of temporary face-check outages."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import ExternalProviderError, ValidationAppError
from app.services.kyc_service import KYCService


@pytest.fixture
def verified_kyc():
    return SimpleNamespace(id_number_encrypted="encrypted-nin", status="verified")


def _check(role, results, verified_kyc):
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = verified_kyc
    user = SimpleNamespace(id="tailor-id", role=role)
    with (
        patch("app.services.kyc_service.settings.NIN_FACE_CHECK", True),
        patch("app.core.identity_encryption.decrypt_identity", return_value="test-nin"),
        patch("app.services.verification_documents.read_profile_photo", return_value=b"face-image"),
        patch("app.integrations.kyc.prembly_face.compare_face_with_nin", side_effect=results) as compare,
    ):
        try:
            KYCService(db).check_new_profile_photo(user, "/media/files/photo")
            return compare.call_count, None
        except ValidationAppError as exc:
            return compare.call_count, str(exc)


def test_tailor_retries_transient_provider_error(verified_kyc):
    count, error = _check("tailor", [
        ExternalProviderError("Temporary outage"),
        SimpleNamespace(matched=True),
    ], verified_kyc)
    assert count == 2
    assert error is None


def test_tailor_provider_outage_still_blocks_unverified_change(verified_kyc):
    count, error = _check("tailor", [
        ExternalProviderError("Temporary outage"),
        ExternalProviderError("Temporary outage"),
    ], verified_kyc)
    assert count == 2
    assert "has not been changed" in error


def test_other_roles_are_not_retried(verified_kyc):
    count, error = _check("designer", [ExternalProviderError("Temporary outage")], verified_kyc)
    assert count == 1
    assert "Try again" in error


def test_face_mismatch_is_not_retried_or_accepted(verified_kyc):
    count, error = _check("tailor", [SimpleNamespace(matched=False)], verified_kyc)
    assert count == 1
    assert "doesn't match" in error
