"""Business (KYB) verification workflow for vendors and professional
businesses, mirroring kyc_service.py."""
from sqlalchemy.orm import Session

from app.core.constants import VerificationStatus
from app.core.exceptions import ForbiddenError, NotFoundError


class KYBService:
    def __init__(self, db: Session):
        self.db = db

    def submit(self, *, business_owner_user_id, registration_number: str, document_storage_keys: list[str]):
        from app.integrations.kyc import get_kyc_provider
        from app.models.kyb_verification import KYBVerification
        from app.models.verification_document import VerificationDocument

        provider = get_kyc_provider()
        result = provider.submit_business_verification(
            business_owner_id=str(business_owner_user_id),
            registration_number=registration_number,
            document_urls=document_storage_keys,
        )

        verification = KYBVerification(
            business_owner_user_id=business_owner_user_id,
            business_registration_number=registration_number,
            status=result.status,
        )
        self.db.add(verification)
        self.db.flush()

        for key in document_storage_keys:
            self.db.add(VerificationDocument(kyb_verification_id=verification.id, document_type="business_registration", storage_key=key))
        self.db.commit()
        self.db.refresh(verification)
        return verification

    def review(self, verification_id, *, reviewer, approve: bool, rejection_reason: str | None = None):
        from app.models.kyb_verification import KYBVerification

        if reviewer.role != "admin":
            raise ForbiddenError("Only an admin can review verifications.")
        verification = self.db.get(KYBVerification, verification_id)
        if not verification:
            raise NotFoundError("Verification not found.")

        verification.status = VerificationStatus.VERIFIED.value if approve else VerificationStatus.REJECTED.value
        verification.reviewed_by_user_id = reviewer.id
        if rejection_reason:
            verification.rejection_reason = rejection_reason
        self.db.commit()
        return verification

    def sync_status_from_provider(self, kyb_verification_id: str):
        raise NotImplementedError("Only relevant for async third-party KYB providers, not the default manual flow.")
