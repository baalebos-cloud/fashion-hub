"""Individual (KYC) verification workflow: submission, admin review,
provider sync."""
from sqlalchemy.orm import Session

from app.core.constants import VerificationStatus
from app.core.exceptions import ForbiddenError, NotFoundError


class KYCService:
    def __init__(self, db: Session):
        self.db = db

    def submit(self, *, user_id, id_type: str, document_storage_keys: list[str]):
        from app.integrations.kyc import get_kyc_provider
        from app.models.kyc_verification import KYCVerification
        from app.models.verification_document import VerificationDocument

        provider = get_kyc_provider()
        result = provider.submit_identity_verification(user_id=str(user_id), id_type=id_type, document_urls=document_storage_keys)

        verification = KYCVerification(user_id=user_id, id_type=id_type, status=result.status)
        self.db.add(verification)
        self.db.flush()

        for key in document_storage_keys:
            self.db.add(VerificationDocument(kyc_verification_id=verification.id, document_type=id_type, storage_key=key))
        self.db.commit()
        self.db.refresh(verification)
        return verification

    def review(self, verification_id, *, reviewer, approve: bool, rejection_reason: str | None = None):
        from app.models.kyc_verification import KYCVerification

        if reviewer.role != "admin":
            raise ForbiddenError("Only an admin can review verifications.")
        verification = self.db.get(KYCVerification, verification_id)
        if not verification:
            raise NotFoundError("Verification not found.")

        verification.status = VerificationStatus.VERIFIED.value if approve else VerificationStatus.REJECTED.value
        verification.reviewed_by_user_id = reviewer.id
        if rejection_reason:
            verification.rejection_reason = rejection_reason
        self.db.commit()

        from app.workers.notification_tasks import notify_order_status_changed_task  # placeholder reuse
        return verification

    def sync_status_from_provider(self, kyc_verification_id: str):
        raise NotImplementedError("Only relevant for async third-party KYC providers, not the default manual flow.")

    def get_document_url(self, document_id, *, requesting_user):
        """Access-controlled: only the document owner or an admin may
        resolve a signed URL for a private KYC/KYB document."""
        raise NotImplementedError("Verify ownership, then call StorageProvider.get_signed_url.")
