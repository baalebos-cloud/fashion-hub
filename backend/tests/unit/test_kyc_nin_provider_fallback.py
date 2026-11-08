"""Provider outage must never fabricate a verified NIN."""
from unittest.mock import Mock, patch
from uuid import uuid4
from app.core.exceptions import ExternalProviderError
from app.services.kyc_service import KYCService


def test_unavailable_nin_provider_queues_unverified_manual_review():
    user = Mock(id=uuid4(), full_name="Test Customer", home_location_id=None)
    db = Mock()
    db.get.return_value = user
    db.add = Mock()
    provider = Mock()
    provider.verify.side_effect = ExternalProviderError("Provider unavailable")
    review = Mock()
    review.submit_identity_verification.return_value = Mock(status="pending")
    with patch("app.integrations.kyc.get_nin_provider", return_value=provider), \
         patch("app.integrations.kyc.get_kyc_provider", return_value=review), \
         patch("app.core.identity_encryption.encrypt_identity", return_value="encrypted"), \
         patch("app.core.identity_encryption.identity_fingerprint", return_value="f" * 64):
        result = KYCService(db).submit(
            user_id=user.id, nin_number="12345678901",
            document_storage_keys=["private/kyc/test-document.pdf"],
            home_latitude=7.64037, home_longitude=5.22102,
            home_formatted_address="Ado Ekiti, Ekiti, Nigeria",
        )
    assert result.status == "under_review"
    assert result.nin_verified_full_name is None
    assert result.identity_match is None
    db.commit.assert_called_once()
