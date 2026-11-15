"""Disputes: a buyer reports a problem with a paid order; an admin resolves it.

- Only the order's buyer can open one, only after payment, and only one open dispute per order.
- While it's open, the seller's payout for the order is held (payout_release_service.blocker).
- Resolving with a refund goes through RefundService (requested, then approved by the admin), so
  every refund rule still applies; the route asks for an authenticator code first.
"""
from decimal import Decimal, InvalidOperation

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.core.timezone import utcnow
from app.models.audit_log import AuditLog
from app.models.dispute import DISPUTE_OUTCOMES, DISPUTE_REASONS, Dispute
from app.models.notification import Notification
from app.models.order import Order
from app.models.user import User

# Orders a buyer can dispute: paid, not cancelled or already refunded.
DISPUTABLE = {
    "paid", "accepted", "in_production", "ready_for_delivery", "shipped", "out_for_delivery", "delivered",
    "received", "completed", "confirmed", "processing", "ready_for_pickup", "picked_up", "in_transit",
}
REASON_LABELS = {
    "not_delivered": "Not delivered", "wrong_item": "Wrong item", "wrong_size": "Wrong size or fit",
    "damaged": "Damaged", "poor_quality": "Poor quality", "other": "Something else",
}
OUTCOME_LABELS = {"refund": "Refund", "remake": "Remake or alteration", "no_action": "No action"}


class DisputeService:
    def __init__(self, db: Session):
        self.db = db

    def _notify(self, user_id, title: str, body: str) -> None:
        self.db.add(Notification(recipient_user_id=user_id, channel="in_app", event_type="order.dispute",
                                 title=title, body=body[:1000]))

    def open(self, *, order_id, actor: User, reason: str, description: str) -> Dispute:
        if reason not in DISPUTE_REASONS:
            raise ValidationAppError("Choose what went wrong.")
        text = " ".join((description or "").split())
        if not 10 <= len(text) <= 2000:
            raise ValidationAppError("Describe the problem in 10 to 2000 characters.")
        order = self.db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order or str(order.buyer_user_id) != str(actor.id):
            raise NotFoundError("Order not found.")
        if order.status not in DISPUTABLE:
            raise ConflictError("You can report a problem once the order is paid (and not cancelled or refunded).")
        if self.db.query(Dispute.id).filter(Dispute.order_id == order.id, Dispute.status == "open").first():
            raise ConflictError("There's already an open dispute on this order. Tailora will get back to you.")
        dispute = Dispute(order_id=order.id, opened_by_user_id=actor.id, reason=reason, description=text, status="open")
        self.db.add(dispute)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("There's already an open dispute on this order. Tailora will get back to you.") from None
        self.db.add(AuditLog(actor_user_id=actor.id, action="dispute.opened", resource_type="order",
                             resource_id=order.id, metadata_json={"dispute_id": str(dispute.id), "reason": reason}))
        self._notify(order.seller_user_id, "A customer reported a problem",
                     f"Order {order.order_number}: {REASON_LABELS[reason]}. Tailora will review it; the payout for this "
                     "order is on hold until then.")
        self.db.commit()
        self.db.refresh(dispute)
        return dispute

    def for_user(self, user: User, *, order_id=None) -> list[Dispute]:
        """Disputes on orders this person bought or sold."""
        q = (self.db.query(Dispute).join(Order, Order.id == Dispute.order_id)
             .filter((Order.buyer_user_id == user.id) | (Order.seller_user_id == user.id)))
        if order_id is not None:
            q = q.filter(Dispute.order_id == order_id)
        return q.order_by(Dispute.created_at.desc()).limit(100).all()

    def admin_list(self, *, status: str | None, offset: int, limit: int):
        q = self.db.query(Dispute)
        if status:
            q = q.filter(Dispute.status == status)
        total = q.count()
        return total, q.order_by(Dispute.created_at.desc()).offset(offset).limit(limit).all()

    def resolve(self, dispute_id, *, admin: User, outcome: str, note: str, refund_amount=None) -> Dispute:
        if admin.role != "admin":
            raise ForbiddenError("Only Tailora's team can resolve disputes.")
        if outcome not in DISPUTE_OUTCOMES:
            raise ValidationAppError("Choose an outcome.")
        note = " ".join((note or "").split())
        if not 5 <= len(note) <= 2000:
            raise ValidationAppError("Explain the decision in 5 to 2000 characters; both sides will see it.")
        dispute = self.db.query(Dispute).filter(Dispute.id == dispute_id).with_for_update().first()
        if not dispute:
            raise NotFoundError("Dispute not found.")
        if dispute.status != "open":
            raise ConflictError("This dispute has already been resolved.")
        order = self.db.get(Order, dispute.order_id)
        if outcome == "refund":
            try:
                amount = Decimal(str(refund_amount))
            except (InvalidOperation, TypeError, ValueError):
                raise ValidationAppError("Enter the refund amount.") from None
            if amount <= 0 or amount > Decimal(str(order.total_amount)):
                raise ValidationAppError("The refund must be more than ₦0 and no more than the order total.")
            from app.services.refund_service import RefundService
            refunds = RefundService(self.db)
            refund = refunds.request_refund(order_id=order.id, requested_by=admin, amount=amount,
                                            reason=f"Dispute: {REASON_LABELS[dispute.reason]}. {note}"[:2000],
                                            idempotency_key=f"dispute-{dispute.id}")
            if refund.status == "requested":  # a retry after a failure finds it already approved
                refund = refunds.approve_refund(refund.id, approved_by=admin)
            dispute = self.db.query(Dispute).filter(Dispute.id == dispute_id).with_for_update().first()
            dispute.refund_amount, dispute.refund_id = amount, refund.id
        dispute.status, dispute.outcome, dispute.resolution_note = "resolved", outcome, note
        dispute.resolved_by_user_id, dispute.resolved_at = admin.id, utcnow()
        self.db.add(AuditLog(actor_user_id=admin.id, action="dispute.resolved", resource_type="order",
                             resource_id=order.id, metadata_json={"dispute_id": str(dispute.id), "outcome": outcome}))
        message = f"Order {order.order_number}: {OUTCOME_LABELS[outcome]}. {note}"
        self._notify(order.buyer_user_id, "Your dispute was resolved", message)
        self._notify(order.seller_user_id, "A dispute on your order was resolved", message)
        self.db.commit()
        self.db.refresh(dispute)
        return dispute
