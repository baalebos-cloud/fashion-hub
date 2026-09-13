"""Refund request/approval/processing workflow."""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.order import Order
from app.models.payment import Payment
from app.models.refund import Refund
from app.models.user import User


class RefundService:
    def __init__(self, db: Session):
        self.db = db

    def request_refund(self, *, order_id, requested_by: User, amount: float, reason: str) -> Refund:
        order = self.db.get(Order, order_id)
        if not order:
            raise NotFoundError("Order not found.")
        if str(order.buyer_user_id) != str(requested_by.id) and requested_by.role != "admin":
            raise ForbiddenError("Only the buyer or an admin can request a refund for this order.")

        payment = self.db.query(Payment).filter(Payment.order_id == order.id).first()
        if not payment or payment.status != "successful":
            raise ConflictError("Cannot refund an order that has not been successfully paid.")

        refund = Refund(
            payment_id=payment.id,
            order_id=order.id,
            requested_by_user_id=requested_by.id,
            amount=amount,
            reason=reason,
            status="requested",
        )
        self.db.add(refund)
        self.db.commit()
        self.db.refresh(refund)
        return refund

    def approve_refund(self, refund_id, *, approved_by: User) -> Refund:
        if approved_by.role != "admin":
            raise ForbiddenError("Only an admin can approve refunds.")
        refund = self.db.get(Refund, refund_id)
        if not refund:
            raise NotFoundError("Refund not found.")
        refund.status = "approved"
        self.db.commit()

        from app.workers.payment_tasks import process_refund_task
        process_refund_task.delay(refund_id=str(refund.id))
        return refund
