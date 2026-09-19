"""Individual (KYC) verification workflow: submission, admin review,
provider sync. NIN verification is COMPULSORY -- see submit()."""
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.core.constants import VerificationStatus
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError

# How closely the NIN record's name must match the account's stated name
# to auto-flag identity_match=True. Below this, the submission still goes
# to admin review (never silently rejected) but is flagged for a closer
# look -- accounts for minor formatting differences (middle names,
# capitalization) without accepting a wildly different name.
NAME_MATCH_THRESHOLD = 0.7


class KYCService:
    def __init__(self, db: Session):
        self.db = db

    def submit(
        self,
        *,
        user_id,
        nin_number: str,
        document_storage_keys: list[str],
        home_latitude: float,
        home_longitude: float,
        home_formatted_address: str | None = None,
    ):
        """
        NIN verification is compulsory for every professional, vendor
        business-owner, and delivery partner (see docs/nin-verification.md)
        -- this method is the one place that enforces it. The NIN lookup's
        OWN name/DOB/gender are what gets stored as the verified record;
        the account's self-reported full_name is only used for the
        similarity check below, never overwritten from it automatically
        (an admin makes that call during review, per identity_match).
        """
        from app.integrations.kyc import get_kyc_provider, get_nin_provider
        from app.models.kyc_verification import KYCVerification
        from app.models.location import Location
        from app.models.user import User
        from app.models.verification_document import VerificationDocument

        user = self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User not found.")

        nin_provider = get_nin_provider()
        nin_result = nin_provider.verify(nin_number)  # raises on invalid/not-found NIN

        similarity = SequenceMatcher(None, user.full_name.lower().strip(), nin_result.full_name.lower().strip()).ratio()
        identity_match = similarity >= NAME_MATCH_THRESHOLD

        home_location = Location(
            latitude=home_latitude,
            longitude=home_longitude,
            location_type="customer_address",  # closest existing LocationType for a personal residence
            formatted_address=home_formatted_address,
        )
        self.db.add(home_location)
        self.db.flush()
        user.home_location_id = home_location.id

        # Document-review provider (ID photos etc.) still runs alongside
        # the NIN lookup -- NIN confirms identity; the document-review
        # queue (get_kyc_provider) is where an admin visually inspects
        # whatever supporting documents were uploaded.
        document_provider = get_kyc_provider()
        document_result = document_provider.submit_identity_verification(
            user_id=str(user_id), id_type="nin", document_urls=document_storage_keys
        )

        # Never store the raw NIN in plaintext in a real deployment --
        # id_number_encrypted is a placeholder for an encryption-at-rest
        # layer (see the model's docstring); it is NEVER returned by any
        # API response (schemas/kyc.py has no nin_number field).
        verification = KYCVerification(
            user_id=user_id,
            id_type="nin",
            id_number_encrypted=nin_number,
            nin_verified_full_name=nin_result.full_name,
            nin_verified_date_of_birth=nin_result.date_of_birth,
            nin_verified_gender=nin_result.gender,
            identity_match=identity_match,
            status=document_result.status,
        )
        self.db.add(verification)
        self.db.flush()

        for key in document_storage_keys:
            self.db.add(VerificationDocument(kyc_verification_id=verification.id, document_type="nin", storage_key=key))

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

        if approve and verification.identity_match is False:
            # Not a hard block -- an admin may still approve after manual
            # review (e.g. a legal name change) -- but require an explicit
            # reason on file when overriding a flagged mismatch.
            if not rejection_reason:
                raise ValidationAppError(
                    "This submission's name didn't closely match its NIN record. "
                    "Add a note explaining the override before approving."
                )

        verification.status = VerificationStatus.VERIFIED.value if approve else VerificationStatus.REJECTED.value
        verification.reviewed_by_user_id = reviewer.id
        if rejection_reason:
            verification.rejection_reason = rejection_reason
        self.db.commit()
        return verification

    def sync_status_from_provider(self, kyc_verification_id: str):
        raise NotImplementedError("Only relevant for async third-party KYC providers, not the default manual flow.")

    def get_document_url(self, document_id, *, requesting_user):
        """Access-controlled: only the document owner or an admin may
        resolve a signed URL for a private KYC/KYB document."""
        raise NotImplementedError("Verify ownership, then call StorageProvider.get_signed_url.")
