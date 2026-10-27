"""Safe payment refunds. Money movement is disabled until provider onboarding passes."""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.core.policies import money_to_minor_units
from app.core.timezone import utcnow
from app.models.order import Order
from app.models.payment import Payment
from app.models.refund import Refund
from app.models.user import User

RESERVED = {"requested", "approved", "processing", "pending", "needs_attention", "manual_review", "processed"}


class RefundService:
    def __init__(self, db: Session):
        self.db = db

    def request_refund(self, *, order_id, requested_by: User, amount, reason: str) -> Refund:
        order = self.db.get(Order, order_id)
        if not order:
            raise NotFoundError("Order not found.")
        if requested_by.role != "admin" and order.buyer_user_id != requested_by.id:
            raise ForbiddenError("Only the buyer or an admin can request this refund.")
        payment = (self.db.query(Payment).filter(Payment.order_id == order.id)
                   .with_for_update().populate_existing().first())
        if not payment or payment.status != "successful":
            raise ConflictError("Only settled payments are refundable.")
        if payment.provider != settings.PAYMENT_PROVIDER:
            raise ConflictError("The original payment provider is not currently configured.")
        amount = Decimal(str(amount))
        try:
            money_to_minor_units(amount)
        except ValueError:
            raise ValidationAppError("Refund amount must be a positive two-decimal value.") from None
        if not reason or len(reason.strip()) < 5 or len(reason) > 2000:
            raise ValidationAppError("Provide a refund reason between 5 and 2000 characters.")
        already_reserved = sum((
            Decimal(str(row.amount)) for row in
            self.db.query(Refund).filter(Refund.payment_id == payment.id,
                                         Refund.status.in_(RESERVED)).all()
        ), Decimal("0.00"))
        if already_reserved + amount > Decimal(str(payment.amount)):
            raise ConflictError("Refund exceeds the remaining refundable balance.")
        refund = Refund(
            payment_id=payment.id, order_id=order.id,
            requested_by_user_id=requested_by.id, amount=amount,
            reason=reason.strip(), status="requested",
        )
        self.db.add(refund)
        self.db.commit()
        self.db.refresh(refund)
        return refund

    def approve_refund(self, refund_id, *, approved_by: User) -> Refund:
        if approved_by.role != "admin":
            raise ForbiddenError("Only an admin can approve refunds.")
        refund = self.db.query(Refund).filter(Refund.id == refund_id).with_for_update().first()
        if not refund:
            raise NotFoundError("Refund not found.")
        if refund.status != "requested":
            raise ConflictError("Refund is no longer awaiting approval.")
        refund.status = "approved"
        self.db.commit()
        if settings.REFUND_EXECUTION_ENABLED:
            # The worker records its processing attempt before calling a provider.
            # A broker outage leaves approved work available for supervised recovery.
            try:
                from app.workers.payment_tasks import process_refund_task
                process_refund_task.delay(refund_id=str(refund.id))
            except Exception:
                from app.core.logging import get_logger
                get_logger(__name__).warning("Approved refund remains pending supervised dispatch.")
        return refund

    def reject_refund(self, refund_id, *, rejected_by: User) -> Refund:
        if rejected_by.role != "admin":
            raise ForbiddenError("Only an admin can reject refunds.")
        refund = self.db.query(Refund).filter(Refund.id == refund_id).with_for_update().first()
        if not refund:
            raise NotFoundError("Refund not found.")
        if refund.status != "requested":
            raise ConflictError("Only unapproved refund requests can be rejected.")
        refund.status = "rejected"
        self.db.commit()
        return refund

    def record_paystack_event(self, *, event_type: str, payload: dict) -> bool:
        """Reconcile only a uniquely identifiable approved refund with a signed webhook.

        Never credit an order based on an email, a guessed amount, or an
        unmatched callback. Duplicate notifications are idempotent.
        """
        from app.core.timezone import utcnow
        from app.core.policies import money_to_minor_units

        reference = payload.get("transaction_reference")
        status = event_type.removeprefix("refund.")
        if not isinstance(reference, str) or not reference or status not in {
            "pending", "processing", "needs-attention", "failed", "processed"
        }:
            return False
        payment = (self.db.query(Payment)
                   .filter(Payment.provider == "paystack",
                           Payment.provider_reference == reference)
                   .with_for_update().first())
        if not payment or payload.get("currency") != payment.currency:
            return False
        try:
            minor = int(str(payload.get("amount", "")))
        except (ValueError, TypeError):
            return False
        if minor <= 0:
            return False
        candidates = (self.db.query(Refund)
                      .filter(Refund.payment_id == payment.id,
                              Refund.status.in_({
                                  "approved", "processing", "pending", "needs_attention",
                                  "manual_review", "processed",
                              }))
                      .with_for_update().all())
        candidates = [r for r in candidates if money_to_minor_units(r.amount) == minor]
        refund_id = payload.get("id")
        if refund_id is not None:
            matched = [r for r in candidates if r.provider_refund_reference == str(refund_id)]
            if matched:
                candidates = matched
            else:
                candidates = [r for r in candidates if r.provider_refund_reference is None]
        if len(candidates) != 1:
            return False
        refund = candidates[0]
        target = "needs_attention" if status == "needs-attention" else status
        # A delayed pending notification cannot regress a processed refund.
        if refund.status == "processed":
            return True
        if refund.status == "failed" or refund.status == "requested":
            return False
        refund.status = target
        if refund_id is not None and refund.provider_refund_reference is None:
            refund.provider_refund_reference = str(refund_id)[:128]
        if target == "processed":
            refund.processed_at = utcnow()
        self.db.commit()
        return True
