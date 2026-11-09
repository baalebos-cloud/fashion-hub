"""Sending sellers their money (owner's choice: automatically once the customer confirms receipt).

A Payout row is created when an order is paid (payout_service.py), with status "pending". A background
job (workers/payout_tasks.py, every few minutes) sends each pending payout through Paystack Transfers
when ALL of these hold:

- payouts are switched on (PAYOUTS_ENABLED) and Paystack is the payment provider;
- the customer has confirmed receipt (order "received" or "completed");
- no refund on the order is requested, approved or done, and no delivery problem is still open;
- the seller is active and has a bank account checked with Paystack whose name matches their verified
  NIN name or business name;
- an admin hasn't held it.

Anything that blocks a payout puts it on hold with the reason (admins can release it). A transfer's
outcome arrives as a Paystack webhook (transfer.success / failed / reversed); transfers still
"processing" after PAYOUT_CHECK_AFTER_MINUTES are checked with Paystack directly. A failed transfer
can be retried by an admin. The same transfer reference is never sent twice.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, ExternalProviderError, NotFoundError
from app.core.timezone import utcnow
from app.integrations.payments import paystack_transfers as paystack
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.order import Order
from app.models.payout import Payout
from app.models.refund import Refund
from app.models.seller_bank_account import SellerBankAccount
from app.models.user import User

logger = logging.getLogger(__name__)

RECEIVED = {"received", "completed"}
# Every refund state that holds money back or may already have returned it (shared with refund_service).
from app.services.refund_service import RESERVED as OPEN_REFUND  # noqa: E402


def payouts_on() -> bool:
    return (settings.PAYOUTS_ENABLED and (settings.PAYMENT_PROVIDER or "").lower() == "paystack"
            and bool(settings.PAYMENT_SECRET_KEY))


def _naira(amount) -> str:
    return f"₦{Decimal(str(amount)):,.2f}"


class PayoutReleaseService:
    def __init__(self, db: Session):
        self.db = db

    # ---- why a payout can't be sent ---------------------------------------------------------------
    def blocker(self, payout: Payout, order: Order | None) -> str | None:
        if order is None:
            return "The order no longer exists."
        refund = (self.db.query(Refund.status).filter(Refund.order_id == order.id, Refund.status.in_(OPEN_REFUND))
                  .first())
        if refund is not None:
            return "A refund on this order is open or done."
        if self._open_delivery_problem(order):
            return "A delivery problem on this order is still open."
        seller = self.db.get(User, payout.seller_user_id)
        if seller is None or not seller.is_active:
            return "The seller's account is closed."
        account = self.db.query(SellerBankAccount).filter(SellerBankAccount.user_id == payout.seller_user_id).first()
        if account is None:
            return "The seller hasn't added a bank account yet."
        if not account.name_matches:
            return "The bank account name doesn't match the seller's verified name. Check it, then release."
        if Decimal(str(payout.net_amount)) <= 0:
            return "Nothing to pay."
        return None

    def _open_delivery_problem(self, order: Order) -> bool:
        from app.models.delivery import Delivery
        from app.models.delivery_issue import DispatchIssueReport
        return (self.db.query(DispatchIssueReport.id).join(Delivery, Delivery.id == DispatchIssueReport.delivery_id)
                .filter(Delivery.order_id == order.id, DispatchIssueReport.status == "OPEN").first() is not None)

    # ---- the background job -----------------------------------------------------------------------
    def release_ready(self, limit: int = 50) -> dict:
        """Send every payout that's due. Safe to run from several workers at once."""
        counts = {"sent": 0, "held": 0, "failed": 0}
        if not payouts_on():
            return counts
        candidates = (self.db.query(Payout.id).join(Order, Order.id == Payout.order_id)
                      .filter(Payout.status == "pending", Order.status.in_(RECEIVED))
                      .order_by(Payout.created_at).limit(limit).all())
        for (payout_id,) in candidates:
            outcome = self._release_one(payout_id)
            if outcome in counts:
                counts[outcome] += 1
        return counts

    def _release_one(self, payout_id) -> str | None:
        payout = (self.db.query(Payout).filter(Payout.id == payout_id, Payout.status == "pending")
                  .with_for_update(skip_locked=True).first())
        if payout is None:
            self.db.rollback()
            return None  # another worker has it, or it changed
        order = self.db.get(Order, payout.order_id)
        if order is None or order.status not in RECEIVED:
            self.db.rollback()
            return None
        reason = self.blocker(payout, order)
        if reason:
            payout.status, payout.hold_reason = "held", reason[:255]
            self._notify(payout, "Payout on hold", f"Your payout of {_naira(payout.net_amount)} for order "
                         f"{order.order_number} is on hold: {reason}")
            self._audit(payout, "payout.held", {"reason": reason[:255], "automatic": True})
            self.db.commit()
            return "held"
        return self._send(payout, order)

    def _send(self, payout: Payout, order: Order) -> str:
        account = self.db.query(SellerBankAccount).filter(SellerBankAccount.user_id == payout.seller_user_id).one()
        payout.attempts = (payout.attempts or 0) + 1
        payout.transfer_reference = f"payout-{payout.id.hex}-{payout.attempts}"
        payout.status, payout.processing_at, payout.failure_reason = "processing", utcnow(), None
        self.db.commit()  # record the reference first, so a crash can't lead to a second transfer
        amount_kobo = int((Decimal(str(payout.net_amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        try:
            result = paystack.initiate_transfer(amount_kobo=amount_kobo, recipient_code=account.recipient_code,
                                                reference=payout.transfer_reference,
                                                reason=f"Tailora order {order.order_number}")
        except paystack.TransferOutcomeUnknown as exc:
            # It may have gone through: stay "processing" under this reference until Paystack's webhook
            # or reconcile_processing() says what happened. Never retried with a new reference first.
            self._audit(payout, "payout.outcome_unknown", {"reason": str(exc)[:255], "reference": payout.transfer_reference})
            self.db.commit()
            return "sent"
        except ExternalProviderError as exc:
            return self._fail(payout, str(exc))  # Paystack clearly refused it
        payout.transfer_code = result.transfer_code
        if result.status == "otp":
            return self._fail(payout, "Paystack asked for an OTP. Turn off OTP for transfers in the Paystack "
                                      "dashboard (Settings › Preferences), then retry.")
        if result.status == "success":
            return self._paid(payout)
        if result.status in {"failed", "reversed"}:
            return self._fail(payout, f"Paystack: transfer {result.status}.")
        self._audit(payout, "payout.sent", {"reference": payout.transfer_reference})
        self.db.commit()
        return "sent"

    def _paid(self, payout: Payout) -> str:
        payout.status, payout.released_at, payout.failure_reason = "paid", utcnow(), None
        order = self.db.get(Order, payout.order_id)
        self._notify(payout, "Payout sent", f"{_naira(payout.net_amount)} for order "
                     f"{order.order_number if order else ''} has been sent to your bank account.")
        self._audit(payout, "payout.paid", {"reference": payout.transfer_reference})
        self.db.commit()
        return "sent"

    def _fail(self, payout: Payout, reason: str) -> str:
        payout.status, payout.failure_reason = "failed", reason[:255]
        self._audit(payout, "payout.failed", {"reason": reason[:255], "reference": payout.transfer_reference})
        self.db.commit()
        logger.warning("payout_failed payout=%s", payout.id)
        return "failed"

    # ---- Paystack's answer ------------------------------------------------------------------------
    def _by_reference(self, reference: str) -> Payout | None:
        """References look like payout-<payout id hex>-<attempt>; older attempts still find their payout."""
        import re
        import uuid as _uuid
        found = re.fullmatch(r"payout-([0-9a-f]{32})-\d+", reference or "")
        if not found:
            return None
        return self.db.query(Payout).filter(Payout.id == _uuid.UUID(found.group(1))).with_for_update().first()

    def record_transfer_event(self, *, event: str, data: dict) -> bool:
        reference = str(data.get("reference") or "")
        payout = self._by_reference(reference)
        if payout is None:
            return False
        current = reference == payout.transfer_reference
        if event == "transfer.success":
            if payout.status == "paid":
                if not current:  # a second attempt also paid: money went out twice
                    logger.error("payout_paid_twice payout=%s", payout.id)
                    self._audit(payout, "payout.duplicate_success", {"reference": reference})
                    self.db.commit()
                return True  # otherwise a repeated webhook
            payout.transfer_reference = reference  # a late success for an earlier attempt still counts
            self._paid(payout)
        elif event in {"transfer.failed", "transfer.reversed"}:
            if not current:
                return True  # an old attempt; the current one decides
            was_paid = payout.status == "paid"
            self._fail(payout, f"Paystack: transfer {event.split('.')[1]}" + (" after it was paid." if was_paid else "."))
            if was_paid:
                payout.released_at = None
                self._notify(payout, "Payout returned", f"The transfer of {_naira(payout.net_amount)} was returned by "
                             "the bank. Check your payout account; Tailora will retry.")
                self.db.commit()
        return True

    def reconcile_processing(self) -> int:
        """Ask Paystack about transfers that have been processing for a while (a missed webhook)."""
        if not payouts_on():
            return 0
        cutoff = utcnow() - timedelta(minutes=settings.PAYOUT_CHECK_AFTER_MINUTES)
        checked = 0
        for payout in (self.db.query(Payout).filter(Payout.status == "processing", Payout.processing_at < cutoff)
                       .limit(50).all()):
            try:
                result = paystack.verify_transfer(payout.transfer_reference)
            except paystack.TransferNotFound:
                self._fail(payout, "Paystack has no record of this transfer; it can be retried.")
                checked += 1
                continue
            except ExternalProviderError:
                continue
            checked += 1
            if result.status == "success":
                self._paid(payout)
            elif result.status in {"failed", "reversed"}:
                self._fail(payout, f"Paystack: transfer {result.status}." + (f" {result.reason}" if result.reason else ""))
        return checked

    # ---- admins -----------------------------------------------------------------------------------
    def _get(self, payout_id) -> Payout:
        payout = self.db.query(Payout).filter(Payout.id == payout_id).with_for_update().first()
        if payout is None:
            raise NotFoundError("Payout not found.")
        return payout

    def hold(self, payout_id, *, admin: User, reason: str) -> Payout:
        payout = self._get(payout_id)
        if payout.status not in {"pending", "failed"}:
            raise ConflictError("Only a payout that hasn't been sent can be held.")
        payout.status, payout.hold_reason = "held", (reason.strip() or "Held by an admin.")[:255]
        self._audit(payout, "payout.held", {"reason": payout.hold_reason}, actor=admin)
        self.db.commit()
        return payout

    def release(self, payout_id, *, admin: User) -> Payout:
        """Held or failed -> pending: the job sends it on its next run (if nothing blocks it any more,
        except the bank-name check, which an admin release overrides)."""
        payout = self._get(payout_id)
        if payout.status not in {"held", "failed"}:
            raise ConflictError("Only a held or failed payout can be released.")
        if payout.transfer_reference:
            # Before any new attempt, make sure the last one really didn't go through.
            try:
                last = paystack.verify_transfer(payout.transfer_reference)
            except paystack.TransferNotFound:
                last = None
            except ExternalProviderError:
                raise ConflictError("Paystack couldn't confirm what happened to the last attempt. Try again shortly.") from None
            if last is not None and last.status == "success":
                self._paid(payout)
                return payout
            if last is not None and last.status not in {"failed", "reversed"}:
                payout.status, payout.hold_reason = "processing", None  # still on its way
                self.db.commit()
                return payout
        override_name = payout.hold_reason and "bank account name" in payout.hold_reason
        payout.status, payout.hold_reason = "pending", None
        if override_name:
            account = (self.db.query(SellerBankAccount)
                       .filter(SellerBankAccount.user_id == payout.seller_user_id).first())
            if account is not None:
                account.name_matches = True  # an admin checked the account by hand
        self._audit(payout, "payout.released_by_admin", {"bank_name_override": bool(override_name)}, actor=admin)
        self.db.commit()
        return payout

    def list(self, status: str | None = None, limit: int = 100) -> list[dict]:
        query = self.db.query(Payout, Order, User).join(Order, Order.id == Payout.order_id).join(
            User, User.id == Payout.seller_user_id)
        if status:
            query = query.filter(Payout.status == status)
        return [{"id": str(p.id), "status": p.status, "order_number": o.order_number, "order_status": o.status,
                 "seller_name": u.full_name, "net_amount": float(p.net_amount), "currency": p.currency,
                 "hold_reason": p.hold_reason, "failure_reason": p.failure_reason, "attempts": p.attempts,
                 "paid_at": p.released_at, "created_at": p.created_at}
                for p, o, u in query.order_by(Payout.created_at.desc()).limit(limit).all()]

    # ---- helpers ------------------------------------------------------------------------------------
    def _notify(self, payout: Payout, title: str, body: str) -> None:
        self.db.add(Notification(recipient_user_id=payout.seller_user_id, channel="in_app",
                                 event_type=f"payout.{title.split()[-1].lower()}", title=title, body=body[:1000]))

    def _audit(self, payout: Payout, action: str, details: dict, actor: User | None = None) -> None:
        self.db.add(AuditLog(actor_user_id=actor.id if actor else None, action=action, resource_type="payout",
                             resource_id=payout.id, metadata_json=details))
