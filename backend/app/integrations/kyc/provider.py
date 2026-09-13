"""
Default manual-review KYC/KYB provider: documents are stored and an admin
reviews them via /api/v1/admin, rather than calling a third-party identity
verification API. Swap in a real provider (Smile ID, Youverify, etc.) later
by implementing KYCProvider and registering it below.
"""
import uuid

from app.integrations.kyc.base import KYCProvider, VerificationSubmissionResult


class ManualReviewKYCProvider(KYCProvider):
    def submit_identity_verification(self, *, user_id: str, id_type: str, document_urls: list[str]) -> VerificationSubmissionResult:
        return VerificationSubmissionResult(provider_reference=f"manual-{uuid.uuid4()}", status="pending")

    def submit_business_verification(self, *, business_owner_id: str, registration_number: str, document_urls: list[str]) -> VerificationSubmissionResult:
        return VerificationSubmissionResult(provider_reference=f"manual-{uuid.uuid4()}", status="pending")

    def check_status(self, provider_reference: str) -> str:
        # Status lives in kyc_verifications/kyb_verifications tables,
        # updated directly by admin review actions.
        return "pending"
