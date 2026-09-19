"""
Referral lifecycle: code generation -> signup attribution -> qualification
-> payout.

Hard rule from the product spec: signing up with someone's referral code
earns the referrer NOTHING by itself. A Referral only becomes commission-
worthy once the REFERRED person completes their first successful PAID
order (`qualify_if_applicable`, called from payment_service.py right after
a payment is confirmed) -- this is what prevents someone from farming
commissions with fake signups that never transact.

Commission math: REFERRAL_COMMISSION_SHARE (default 20%) of the
PLATFORM's own commission on that first order -- not a percentage of the
order total itself. So if the platform takes 15% of a ₦10,000 order
(₦1,500), the referrer earns 20% of that ₦1,500 = ₦300. This keeps the
referral program self-funding out of the platform's own take rate rather
than eating into what professionals/vendors net.
"""
import secrets
import string

from sqlalchemy.orm import Session

from app.core.constants import ReferralStatus
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.timezone import utcnow
from app.models.referral import Referral
from app.models.user import User
from app.repositories.referral_repository import ReferralRepository
from app.repositories.user_repository import UserRepository

CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_LENGTH = 8


class ReferralService:
    def __init__(self, db: Session):
        self.db = db
        self.referrals = ReferralRepository(db)
        self.users = UserRepository(db)

    def get_or_create_code(self, user: User) -> str:
        if user.referral_code:
            return user.referral_code

        for _ in range(5):  # collision retries; practically never needed at this code space
            candidate = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if not self.db.query(User).filter(User.referral_code == candidate).first():
                user.referral_code = candidate
                self.db.commit()
                self.db.refresh(user)
                return candidate
        raise RuntimeError("Could not generate a unique referral code after 5 attempts.")

    def record_signup(self, *, referral_code: str, new_user: User) -> Referral:
        """Called from auth_service.py::sign_up when the person entered a
        referral code. Creates a PENDING referral -- no commission implied
        yet."""
        referrer = self.db.query(User).filter(User.referral_code == referral_code).first()
        if not referrer:
            raise ValidationAppError("Invalid referral code.")
        if referrer.id == new_user.id:
            raise ValidationAppError("You cannot refer yourself.")

        existing = self.referrals.get_by_referred_user(new_user.id)
        if existing:
            raise ConflictError("This account has already been attributed to a referral.")

        referral = Referral(
            referrer_user_id=referrer.id,
            referred_user_id=new_user.id,
            referral_code_used=referral_code,
            status=ReferralStatus.PENDING.value,
        )
        self.referrals.add(referral)
        self.db.commit()
        self.db.refresh(referral)
        return referral

    def qualify_if_applicable(self, *, referred_user_id, qualifying_order_id, order_total: float, currency: str) -> None:
        """
        Called once, right after an order's payment is confirmed (see
        payment_service.py). Idempotent: does nothing if this user has no
        pending referral, or if it's already been qualified by an earlier
        order (i.e. only the FIRST successful order counts).
        """
        referral = self.referrals.get_by_referred_user(referred_user_id)
        if not referral or referral.status != ReferralStatus.PENDING.value:
            return

        from app.core.config import settings

        platform_commission = order_total * settings.PLATFORM_COMMISSION_RATE
        commission = platform_commission * settings.REFERRAL_COMMISSION_SHARE

        referral.status = ReferralStatus.QUALIFIED.value
        referral.qualifying_order_id = qualifying_order_id
        referral.qualified_at = utcnow()
        referral.commission_amount = round(commission, 2)
        referral.commission_currency = currency
        self.db.commit()

        from app.workers.notification_tasks import notify_referral_qualified_task
        notify_referral_qualified_task.delay(referral_id=str(referral.id))

    def mark_paid(self, referral_id, *, actor: User) -> Referral:
        if actor.role != "admin":
            from app.core.exceptions import ForbiddenError
            raise ForbiddenError("Only an admin can mark a referral commission as paid.")

        referral = self.db.get(Referral, referral_id)
        if not referral:
            raise NotFoundError("Referral not found.")
        if referral.status != ReferralStatus.QUALIFIED.value:
            raise ConflictError("Only a qualified referral can be marked paid.")

        referral.status = ReferralStatus.PAID.value
        referral.paid_at = utcnow()
        self.db.commit()
        self.db.refresh(referral)
        return referral

    def get_summary_for_user(self, user_id) -> dict:
        referrals = self.referrals.list_for_referrer(user_id, limit=1000)
        qualified_or_paid = [r for r in referrals if r.status in (ReferralStatus.QUALIFIED.value, ReferralStatus.PAID.value)]
        return {
            "total_referred": len(referrals),
            "qualified_count": len(qualified_or_paid),
            "total_earned": sum(float(r.commission_amount or 0) for r in qualified_or_paid),
            "total_paid": sum(float(r.commission_amount or 0) for r in referrals if r.status == ReferralStatus.PAID.value),
            "referrals": referrals,
        }
