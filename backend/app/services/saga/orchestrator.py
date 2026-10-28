"""Guarded event-driven Saga coordinator.

All progress here is a *simulation*. Real payment capture, escrow custody,
refunds and payouts must be verified by an authorized provider integration.
"""
from enum import Enum

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.order import Order
from app.models.saga import SagaStepLog, LedgerEntry


class SagaState(str, Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    ESCROW_HELD = "ESCROW_HELD"
    TAILOR_ACCEPTED = "TAILOR_ACCEPTED"
    MATERIALS_COMMITTED = "MATERIALS_COMMITTED"
    IN_PRODUCTION = "IN_PRODUCTION"
    DISPATCHED = "DISPATCHED"
    COMPLETED = "COMPLETED"
    COMPENSATING = "COMPENSATING"
    CANCELLED_REFUNDED = "CANCELLED_REFUNDED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


NEXT = {
    SagaState.PENDING_PAYMENT: {SagaState.ESCROW_HELD},
    SagaState.ESCROW_HELD: {SagaState.TAILOR_ACCEPTED, SagaState.COMPENSATING},
    SagaState.TAILOR_ACCEPTED: {SagaState.MATERIALS_COMMITTED, SagaState.COMPENSATING},
    SagaState.MATERIALS_COMMITTED: {SagaState.IN_PRODUCTION, SagaState.COMPENSATING},
    SagaState.IN_PRODUCTION: {SagaState.DISPATCHED, SagaState.COMPENSATING},
    SagaState.DISPATCHED: {SagaState.COMPLETED, SagaState.REVIEW_REQUIRED},
    SagaState.COMPENSATING: {SagaState.CANCELLED_REFUNDED, SagaState.REVIEW_REQUIRED},
    SagaState.REVIEW_REQUIRED: set(),
    SagaState.CANCELLED_REFUNDED: set(),
    SagaState.COMPLETED: set(),
}


class SandboxSagaService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _require_sandbox():
        if settings.APP_ENV == "production" or settings.PAYMENTS_ENABLED:
            raise ForbiddenError("Simulated Saga operations are forbidden in production or with live payments.")

    def state(self, order_id):
        self._require_sandbox()
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise NotFoundError("Order not found.")
        record = (self.db.query(SagaStepLog).filter(SagaStepLog.order_id == order_id,
                                                    SagaStepLog.status == "completed")
                  .order_by(SagaStepLog.created_at.desc(), SagaStepLog.id.desc()).first())
        return record.step_name if record else SagaState.PENDING_PAYMENT.value

    def advance(self, *, order_id, actor, target: SagaState, event_key: str,
                provider_confirmed: bool = False):
        self._require_sandbox()
        if not event_key or len(event_key) > 128 or not event_key.isascii():
            raise ConflictError("Valid idempotency event key required.")
        order = self.db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order or order.order_type != "customer_order":
            raise NotFoundError("Clothing order not found.")
        if actor.role != "admin" and str(actor.id) not in {str(order.buyer_user_id), str(order.seller_user_id)}:
            raise ForbiddenError("Not a party to this order.")
        existing = (self.db.query(SagaStepLog).filter(
            SagaStepLog.order_id == order_id,
            SagaStepLog.payload["event_key"].astext == event_key,
        ).first())
        if existing:
            if existing.step_name != target.value:
                raise ConflictError("Idempotency key reused for different Saga step.")
            return existing
        current = SagaState(self.state(order_id))
        if target not in NEXT[current]:
            raise ConflictError(f"Invalid Saga transition {current.value} -> {target.value}.")
        if target in {SagaState.ESCROW_HELD, SagaState.CANCELLED_REFUNDED} and not provider_confirmed:
            raise ConflictError("Provider confirmation is mandatory for hold or refund completion.")
        # Sandbox ledger entries are simulations, never proof of provider custody.
        if target == SagaState.ESCROW_HELD:
            self._journal(order, event_key, "sandbox_customer_receivable", "debit",
                          "sandbox_escrow_liability", "credit")
        if target == SagaState.CANCELLED_REFUNDED:
            self._journal(order, event_key, "sandbox_escrow_liability", "debit",
                          "sandbox_customer_receivable", "credit")
        log = SagaStepLog(order_id=order.id, step_name=target.value, status="completed",
                          payload={"event_key": event_key, "sandbox": True,
                                   "provider_confirmed_mock": provider_confirmed})
        self.db.add(log)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return log

    def _journal(self, order, event_key, debit_account, debit_side, credit_account, credit_side):
        from app.core.policies import money_to_minor_units
        amount = money_to_minor_units(order.total_amount)
        for account, direction in ((debit_account, debit_side), (credit_account, credit_side)):
            self.db.add(LedgerEntry(order_id=order.id, event_key=event_key,
                                    account=account, direction=direction,
                                    amount_minor=amount, currency=order.currency))
