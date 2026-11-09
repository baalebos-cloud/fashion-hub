"""Verification centre: KYB submission, admin decisions, and what "verified" means.

Rules (one place, used by admin review and the user's checklist):
- Tailor/designer and delivery partner: verified once their identity (KYC) is verified.
- Vendor: verified once identity (KYC) AND business (KYB) are both verified.
  KYB is optional for tailors/designers and shows as a trust bonus only.

Approving or rejecting notifies the applicant (with the reason on rejection)
and updates the profile's is_verified flag, which drives the public verified
badge, shop links and rider eligibility.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ExternalProviderError, ForbiddenError, NotFoundError, ValidationAppError
from app.core.timezone import utcnow
from app.models.delivery_partner import DeliveryPartner
from app.models.kyb_verification import KYBVerification
from app.models.kyc_verification import KYCVerification
from app.models.notification import Notification
from app.models.professional import Professional
from app.models.user import User
from app.models.vendor import Vendor
from app.models.verification_document import VerificationDocument
from app.services.kyb_matching import evaluate as evaluate_business

OPEN_STATUSES = {"pending", "under_review"}
KYB_ROLES = {"vendor", "tailor", "designer"}
KYC_ROLES = {"tailor", "designer", "vendor", "delivery_partner"}
COMPANY_NAME_MATCH = 0.6
_COMPANY_SUFFIXES = re.compile(r"\b(limited|ltd|plc|enterprises?|ventures?|nig(eria)?|global|services?|and|&)\b")


def normalize_registration(raw: str, company_type: str) -> str:
    """Accept 'RC 1234567', 'rc-1234567', 'BN1234567' or plain digits; store digits only."""
    digits = re.sub(r"^(rc|bn|it)\s*[-/]?\s*", "", raw.strip().lower())
    digits = re.sub(r"[\s-]", "", digits)
    if not re.fullmatch(r"\d{4,8}", digits):
        raise ValidationAppError(f"Enter your {company_type} number, e.g. {company_type} 1234567.")
    return digits


def company_names_match(a: str | None, b: str | None) -> bool | None:
    if not a or not b:
        return None
    def clean(value: str) -> str:
        return re.sub(r"\s+", " ", _COMPANY_SUFFIXES.sub(" ", re.sub(r"[^a-z0-9& ]", " ", value.lower()))).strip()
    return SequenceMatcher(None, clean(a), clean(b)).ratio() >= COMPANY_NAME_MATCH


class VerificationService:
    def __init__(self, db: Session, cac_lookup=None):
        self.db = db
        if cac_lookup is None:
            from app.integrations.kyc.prembly_cac import lookup_cac
            cac_lookup = lookup_cac
        self._cac_lookup = cac_lookup

    # ---- reads -----------------------------------------------------------
    def latest_kyc(self, user_id) -> KYCVerification | None:
        return (self.db.query(KYCVerification).filter(KYCVerification.user_id == user_id)
                .order_by(KYCVerification.created_at.desc()).first())

    def latest_kyb(self, user_id) -> KYBVerification | None:
        return (self.db.query(KYBVerification).filter(KYBVerification.business_owner_user_id == user_id)
                .order_by(KYBVerification.created_at.desc()).first())

    def _business_name(self, user: User) -> str | None:
        if user.role == "vendor":
            vendor = self.db.query(Vendor).filter(Vendor.user_id == user.id).first()
            return vendor.business_name if vendor else None
        pro = self.db.query(Professional).filter(Professional.user_id == user.id).first()
        return pro.business_name if pro else None

    # ---- KYB submission ---------------------------------------------------
    def submit_kyb(self, *, user: User, registration_number: str, company_type: str,
                   document_storage_keys: list[str]) -> KYBVerification:
        if user.role not in KYB_ROLES:
            raise ForbiddenError("Business verification is for vendors, tailors and designers.")
        from app.core.profile_photo import require_profile_photo
        require_profile_photo(user)
        if not document_storage_keys:
            raise ValidationAppError("Upload your CAC registration certificate.")
        latest = self.latest_kyb(user.id)
        if latest and latest.status in OPEN_STATUSES:
            raise ConflictError("Your business verification is already being reviewed.")
        if latest and latest.status == "verified":
            raise ConflictError("Your business is already verified.")
        number = normalize_registration(registration_number, company_type)

        verified_name, name_match, status, result = None, None, "pending", None
        try:
            result = self._cac_lookup(number, company_type)
            verified_name = result.company_name
            name_match = company_names_match(self._business_name(user), verified_name)
        except NotFoundError:
            raise ValidationAppError(
                f"We couldn't find {company_type} {number} with CAC. Check the number and business type.") from None
        except ExternalProviderError:
            status = "under_review"  # registry unavailable: an admin checks the certificate by hand

        # One submission per registration number at a time: two accounts sending the same number
        # together are handled one after the other, so the second sees the first (and goes to an admin).
        from sqlalchemy import text
        self.db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                        {"key": f"kyb-cac:{company_type}{number}"})
        duplicate = (self.db.query(KYBVerification.id)
                     .filter(KYBVerification.business_registration_number == number,
                             KYBVerification.company_type == company_type,
                             KYBVerification.business_owner_user_id != user.id,
                             KYBVerification.status.in_(("pending", "under_review", "verified"))).first() is not None)
        kyc = self.latest_kyc(user.id)
        identity_verified = kyc is not None and kyc.status == "verified"
        from app.core.profile_photo import has_photo
        decision = evaluate_business(
            record_found=result is not None, company_status=result.registration_status if result else None,
            business_name_matches=name_match, identity_verified=identity_verified,
            people=result.people if result else [], verified_name=kyc.nin_verified_full_name if kyc else None,
            verified_dob=kyc.nin_verified_date_of_birth if kyc else None,
            has_photo=has_photo(user), duplicate=duplicate)
        from app.core.config import settings
        auto_approve = settings.KYB_AUTO_APPROVE and result is not None and decision["passed"]
        if auto_approve:
            status = "verified"
        elif result is not None and settings.KYB_AUTO_APPROVE:
            status = "under_review"  # an admin looks at the rules that didn't pass

        vendor = self.db.query(Vendor).filter(Vendor.user_id == user.id).first() if user.role == "vendor" else None
        record = KYBVerification(business_owner_user_id=user.id, vendor_id=vendor.id if vendor else None,
                                 business_registration_number=number,
                                 company_type=company_type, provider="prembly" if verified_name else "manual",
                                 verified_company_name=verified_name, name_match=name_match, status=status,
                                 auto_checks=decision, reviewed_at=utcnow() if auto_approve else None)
        self.db.add(record)
        self.db.flush()
        for key in document_storage_keys:
            self.db.add(VerificationDocument(kyb_verification_id=record.id,
                                             document_type="business_registration", storage_key=key))
        if auto_approve:
            self._record_business_auto_approval(user, record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def _record_business_auto_approval(self, user: User, record: KYBVerification) -> None:
        """Same effects as an admin approval: profile badge, notification, audit entry (no personal data)."""
        from app.models.audit_log import AuditLog
        self.apply_profile_verification(user)
        self.db.add(Notification(
            recipient_user_id=user.id, channel="in_app", event_type="verification.kyb.verified",
            title="Business verification approved",
            body="Your CAC record matched your business and lists you as an owner, so your business was "
                 "verified automatically."))
        self.db.add(AuditLog(actor_user_id=None, action="kyb.auto_approved", resource_type="verification",
                             resource_id=record.id, metadata_json={"provider": "prembly",
                                                                   "checks": record.auto_checks["checks"]}))

    # ---- admin decisions ----------------------------------------------------
    def decide(self, *, kind: str, verification_id, admin: User, approve: bool, reason: str | None):
        model = KYCVerification if kind == "kyc" else KYBVerification
        record = (self.db.query(model).filter(model.id == verification_id, model.status.in_(OPEN_STATUSES))
                  .with_for_update().first())
        if record is None:
            raise NotFoundError(f"Open {kind.upper()} submission not found.")
        reason = (reason or "").strip() or None
        if not approve and not reason:
            raise ValidationAppError("Give a reason so the applicant knows what to fix.")
        owner_for_photo = self.db.get(User, record.user_id if kind == "kyc" else record.business_owner_user_id)
        if approve and owner_for_photo is not None:
            from app.core.profile_photo import require_profile_photo
            require_profile_photo(owner_for_photo, message="This person has no profile photo yet. Ask them to add one before approving.")
        flagged = record.identity_match is False if kind == "kyc" else record.name_match is False
        if approve and flagged and not reason:
            raise ValidationAppError("The name didn't match the official record. Add a note explaining the override.")
        record.status = "verified" if approve else "rejected"
        record.rejection_reason = reason
        record.reviewed_by_user_id = admin.id
        record.reviewed_at = utcnow()
        owner_id = record.user_id if kind == "kyc" else record.business_owner_user_id
        owner = self.db.get(User, owner_id)
        if owner is not None:
            self.apply_profile_verification(owner)
            label = "Identity" if kind == "kyc" else "Business"
            self.db.add(Notification(
                recipient_user_id=owner.id, channel="in_app", event_type=f"verification.{kind}.{record.status}",
                title=f"{label} verification {'approved' if approve else 'needs attention'}",
                body=(f"Your {label.lower()} verification was approved."
                      if approve else f"Your {label.lower()} verification was not approved: {reason} Please resubmit."),
            ))
        return record

    def _profile(self, user: User):
        model = {"tailor": Professional, "designer": Professional,
                 "delivery_partner": DeliveryPartner, "vendor": Vendor}.get(user.role)
        return self.db.query(model).filter(model.user_id == user.id).first() if model else None

    def requirements_met(self, user: User) -> bool:
        kyc = self.latest_kyc(user.id)
        kyc_ok = kyc is not None and kyc.status == "verified"
        if user.role == "vendor":
            kyb = self.latest_kyb(user.id)
            return kyc_ok and kyb is not None and kyb.status == "verified"
        return kyc_ok and user.role in KYC_ROLES

    def apply_profile_verification(self, user: User) -> bool:
        """Grant the profile's verified flag once requirements are met. Never revokes:
        profiles verified earlier by an admin stay verified; admins unverify explicitly."""
        if not self.requirements_met(user):
            return False
        profile = self._profile(user)
        if profile is not None:
            profile.is_verified = True
        return True

    # ---- checklist for the user ---------------------------------------------
    def summary(self, user: User) -> dict:
        def step(key, title, record, required, href_hint):
            status = record.status if record else "not_started"
            return {"key": key, "title": title, "required": required, "status": status,
                    "rejection_reason": record.rejection_reason if record and status == "rejected" else None,
                    "submitted_at": record.created_at if record else None, "action": href_hint}

        steps = []
        if user.role in KYC_ROLES:
            steps.append(step("identity", "Identity (NIN)", self.latest_kyc(user.id), True, "kyc"))
        if user.role in KYB_ROLES:
            steps.append(step("business", "Business registration (CAC)", self.latest_kyb(user.id),
                              user.role == "vendor", "kyb"))
        profile = self._profile(user)
        profile_verified = bool(profile and profile.is_verified)  # read-only: never changes state
        pending = [s for s in steps if s["required"] and s["status"] != "verified"]
        if not steps:
            next_step = None
        elif profile_verified:
            next_step = "You're verified. Customers now see the verified badge on your profile."
        elif any(s["status"] == "rejected" for s in pending):
            next_step = "Fix the item marked 'Needs attention' and resubmit."
        elif any(s["status"] == "not_started" for s in pending):
            first = next(s for s in pending if s["status"] == "not_started")
            next_step = f"Start with {first['title']}."
        else:
            next_step = "We're reviewing your documents. You'll get a notification when it's done."
        return {"role": user.role, "verified": profile_verified, "steps": steps, "next_step": next_step}

    # ---- admin queue --------------------------------------------------------
    def admin_queue(self, kind: str, limit: int = 100) -> list[dict]:
        model = KYCVerification if kind == "kyc" else KYBVerification
        owner_col = model.user_id if kind == "kyc" else model.business_owner_user_id
        rows = (self.db.query(model, User).join(User, User.id == owner_col)
                .filter(model.status.in_(OPEN_STATUSES)).order_by(model.created_at).limit(limit).all())
        doc_col = VerificationDocument.kyc_verification_id if kind == "kyc" else VerificationDocument.kyb_verification_id
        documents: dict = {}
        ids = [r.id for r, _ in rows]
        if ids:
            for doc in self.db.query(VerificationDocument).filter(doc_col.in_(ids)):
                documents.setdefault(getattr(doc, "kyc_verification_id" if kind == "kyc" else "kyb_verification_id"),
                                     []).append({"id": str(doc.id), "type": doc.document_type})
        items = []
        for record, owner in rows:
            item = {"id": str(record.id), "status": record.status, "submitted_at": record.created_at,
                    "applicant_name": owner.full_name, "applicant_role": owner.role,
                    "documents": documents.get(record.id, [])}
            if kind == "kyc":
                item.update(official_name=record.nin_verified_full_name, name_match=record.identity_match,
                            registry_checked=record.nin_verified_full_name is not None,
                            # Which automatic-approval rules failed (no personal data).
                            auto_checks=(record.auto_checks or {}).get("checks"),
                            document_note=(record.auto_checks or {}).get("document_note"),
                            document_checked=bool((record.auto_checks or {}).get("document_checked", False)),
                            face=(record.auto_checks or {}).get("face"))
            else:
                item.update(official_name=record.verified_company_name, name_match=record.name_match,
                            registry_checked=record.verified_company_name is not None,
                            business_name=self._business_name(owner),
                            auto_checks=(record.auto_checks or {}).get("checks"),
                            registration=f"{record.company_type or ''} {record.business_registration_number or ''}".strip())
            items.append(item)
        return items
