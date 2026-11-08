"""Individual (KYC) verification workflow: submission, admin review,
provider sync. NIN verification is COMPULSORY -- see submit()."""
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import VerificationStatus
from app.core.timezone import utcnow
from app.services.nin_matching import evaluate, name_matches
from app.core.exceptions import ExternalProviderError, ForbiddenError, NotFoundError, ValidationAppError

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
        home_latitude: float | None,
        home_longitude: float | None,
        home_formatted_address: str | None = None,
        date_of_birth=None,
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

        latest = (self.db.query(KYCVerification).filter(KYCVerification.user_id == user_id)
                  .order_by(KYCVerification.created_at.desc()).first())
        if latest is not None and latest.status in {"pending", "under_review"}:
            from app.core.exceptions import ConflictError
            raise ConflictError("Your identity verification is already being reviewed.")
        if latest is not None and latest.status == "verified":
            from app.core.exceptions import ConflictError
            raise ConflictError("Your identity is already verified.")

        from app.core.identity_encryption import encrypt_identity, identity_fingerprint
        encrypted_nin = encrypt_identity(nin_number)
        fingerprint = identity_fingerprint(nin_number)
        nin_provider = get_nin_provider()
        if len(nin_number) != 11 or not nin_number.isascii() or not nin_number.isdecimal():
            raise ValidationAppError("Enter a valid 11-digit NIN.")
        if not document_storage_keys:
            raise ValidationAppError("Upload a supporting identity document.")
        try:
            nin_result = nin_provider.verify(nin_number)
        except ExternalProviderError:
            # A provider outage never verifies identity. Hold documents for manual review.
            nin_result = None

        identity_match = None
        if nin_result is not None:
            similarity = SequenceMatcher(None, user.full_name.lower().strip(), nin_result.full_name.lower().strip()).ratio()
            identity_match = similarity >= NAME_MATCH_THRESHOLD or name_matches(user.full_name, nin_result.full_name)

        # One submission per NIN at a time: two accounts sending the same NIN together are
        # handled one after the other (lock held until this transaction commits), so the
        # second always sees the first and goes to manual review.
        from sqlalchemy import text
        self.db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": "kyc-nin:" + fingerprint})
        legacy_complete = self._fingerprint_legacy_records()
        # The same NIN on another account (verified or waiting) never goes through automatically.
        duplicate = (self.db.query(KYCVerification.id)
                     .filter(KYCVerification.nin_fingerprint == fingerprint, KYCVerification.user_id != user_id,
                             KYCVerification.status.in_(("pending", "under_review", "verified"))).first() is not None
                     or not legacy_complete)
        from app.core.profile_photo import has_photo as has_profile_photo
        decision = evaluate(account_name=user.full_name,
                            official_name=nin_result.full_name if nin_result is not None else None,
                            entered_dob=date_of_birth,
                            official_dob=nin_result.date_of_birth if nin_result is not None else None,
                            has_photo=has_profile_photo(user), duplicate=duplicate)
        auto_approve = settings.NIN_AUTO_APPROVE and nin_result is not None and decision["passed"]

        if (home_latitude is None) != (home_longitude is None):
            raise ValidationAppError("Supply both coordinates or neither.")
        if home_latitude is None and not (home_formatted_address or "").strip():
            raise ValidationAppError("A home address or confirmed map position is required.")

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
            id_number_encrypted=encrypted_nin,
            nin_verified_full_name=nin_result.full_name if nin_result is not None else None,
            nin_verified_date_of_birth=nin_result.date_of_birth if nin_result is not None else None,
            nin_verified_gender=nin_result.gender if nin_result is not None else None,
            identity_match=identity_match,
            nin_fingerprint=fingerprint,
            auto_checks=decision,
            provider=settings.NIN_PROVIDER if nin_result is not None else "manual",
            status=("verified" if auto_approve
                    else "under_review" if nin_result is None or settings.NIN_AUTO_APPROVE
                    else document_result.status),
            reviewed_at=utcnow() if auto_approve else None,
        )
        self.db.add(verification)
        self.db.flush()

        for key in document_storage_keys:
            self.db.add(VerificationDocument(kyc_verification_id=verification.id, document_type="nin", storage_key=key))

        if auto_approve:
            self._record_auto_approval(user, verification)

        self.db.commit()
        self.db.refresh(verification)
        return verification

    def _fingerprint_legacy_records(self) -> bool:
        """Records from before fingerprints existed get one now, so the duplicate check sees them.
        Migration 0035 does this up front when the key is available; this catches any it missed.
        Returns False if any older record couldn't be fingerprinted: the caller then treats the
        NIN as possibly used elsewhere (manual review) rather than skipping it."""
        from app.core.exceptions import ExternalProviderError as _Unreadable
        from app.core.identity_encryption import decrypt_identity, identity_fingerprint
        from app.models.kyc_verification import KYCVerification
        legacy = (self.db.query(KYCVerification)
                  .filter(KYCVerification.nin_fingerprint.is_(None), KYCVerification.id_number_encrypted.isnot(None),
                          KYCVerification.status.in_(("pending", "under_review", "verified")))
                  .limit(501).all())
        complete = len(legacy) <= 500
        for record in legacy[:500]:
            try:
                record.nin_fingerprint = identity_fingerprint(decrypt_identity(record.id_number_encrypted))
            except _Unreadable:
                complete = False
        if legacy:
            self.db.flush()
        return complete

    def _record_auto_approval(self, user, verification):
        """Same effects as an admin approval: profile badge, notification, audit entry (no personal data)."""
        from app.models.audit_log import AuditLog
        from app.models.notification import Notification
        from app.services.verification_service import VerificationService
        VerificationService(self.db).apply_profile_verification(user)
        self.db.add(Notification(recipient_user_id=user.id, channel="in_app", event_type="verification.kyc.verified",
                                 title="Identity verification approved",
                                 body="Your NIN details matched your account, so your identity was verified automatically."))
        self.db.add(AuditLog(actor_user_id=None, action="kyc.auto_approved", resource_type="verification",
                             resource_id=verification.id,
                             metadata_json={"provider": settings.NIN_PROVIDER, "checks": verification.auto_checks["checks"]}))

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
