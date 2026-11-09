"""A seller's payout bank account: checked with Paystack, protected by their password.

Adding or changing it needs the seller's current password, so a stolen session can't redirect their
money. The bank's account name is compared with the seller's verified NIN name and business name;
automatic payouts only go to a matching account (otherwise an admin checks and releases).
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.core.exceptions import ExternalProviderError, ForbiddenError, ValidationAppError
from app.core.identity_encryption import encrypt_identity
from app.core.security import verify_password
from app.core.timezone import utcnow
from app.integrations.payments import paystack_transfers as paystack
from app.models.audit_log import AuditLog
from app.models.kyc_verification import KYCVerification
from app.models.notification import Notification
from app.models.seller_bank_account import SellerBankAccount
from app.models.user import User
from app.services.nin_matching import name_matches

SELLER_ROLES = {"tailor", "designer", "vendor"}
_banks_cache: list[dict] | None = None


def account_name_matches(account_name: str, *, verified_name: str | None, business_name: str | None) -> bool:
    if verified_name and (name_matches(verified_name, account_name) or name_matches(account_name, verified_name)):
        return True
    if business_name:
        from app.services.verification_service import company_names_match
        return company_names_match(business_name, account_name) is True
    return False


class SellerBankAccountService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def banks() -> list[dict]:
        global _banks_cache
        if _banks_cache is None:
            _banks_cache = paystack.list_banks()
        return _banks_cache

    def get(self, user: User) -> SellerBankAccount | None:
        return self.db.query(SellerBankAccount).filter(SellerBankAccount.user_id == user.id).first()

    def describe(self, account: SellerBankAccount | None) -> dict | None:
        if account is None:
            return None
        return {"bank_name": account.bank_name, "account_last4": account.account_last4,
                "account_name": account.account_name, "name_matches": account.name_matches,
                "verified_at": account.verified_at}

    def set(self, user: User, *, bank_code: str, account_number: str, password: str) -> SellerBankAccount:
        if user.role not in SELLER_ROLES:
            raise ForbiddenError("Only tailors, designers and vendors receive payouts.")
        if not verify_password(password or "", user.hashed_password):
            raise ForbiddenError("That password isn't right.")
        account_number = re.sub(r"\D", "", account_number or "")
        if len(account_number) != 10:
            raise ValidationAppError("Enter your 10-digit account number (NUBAN).")
        bank = next((b for b in self.banks() if b["code"] == bank_code), None)
        if bank is None:
            raise ValidationAppError("Choose your bank from the list.")
        try:
            account_name = paystack.resolve_account(account_number, bank_code)
        except ExternalProviderError as exc:
            raise ValidationAppError(f"That account couldn't be checked: {exc}") from None
        recipient = paystack.create_recipient(name=account_name, account_number=account_number, bank_code=bank_code)
        kyc = (self.db.query(KYCVerification).filter(KYCVerification.user_id == user.id,
                                                     KYCVerification.status == "verified")
               .order_by(KYCVerification.created_at.desc()).first())
        # Only verified records count: the NIN name, or the CAC company name from an approved business
        # check. The self-typed business name on the profile does not.
        from app.models.kyb_verification import KYBVerification
        kyb = (self.db.query(KYBVerification).filter(KYBVerification.business_owner_user_id == user.id,
                                                     KYBVerification.status == "verified")
               .order_by(KYBVerification.created_at.desc()).first())
        matches = account_name_matches(account_name, verified_name=kyc.nin_verified_full_name if kyc else None,
                                       business_name=kyb.verified_company_name if kyb else None)
        account = self.get(user) or SellerBankAccount(user_id=user.id)
        changed = account.id is not None
        account.bank_code, account.bank_name = bank_code, bank["name"][:128]
        account.account_number_encrypted = encrypt_identity(account_number)
        account.account_last4 = account_number[-4:]
        account.account_name, account.name_matches = account_name, matches
        account.recipient_code, account.verified_at = recipient, utcnow()
        self.db.add(account)
        self.db.flush()
        self.db.add(AuditLog(actor_user_id=user.id, action="payout_account.changed" if changed else "payout_account.added",
                             resource_type="seller_bank_account", resource_id=account.id,
                             metadata_json={"bank": bank["name"][:128], "last4": account.account_last4,
                                            "name_matches": matches}))
        self.db.add(Notification(
            recipient_user_id=user.id, channel="in_app", event_type="payout.account_changed",
            title="Payout bank account updated",
            body=f"Payouts now go to {bank['name']} ••••{account.account_last4} ({account_name}). "
                 "If this wasn't you, change your password and contact support."))
        self.db.commit()
        return account
