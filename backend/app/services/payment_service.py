"""
Payment business logic. Two hard rules enforced throughout this file:

1. NEVER trust a client-reported "payment successful" state. The order is
   only marked PAID after `verify_payment` (a server-to-server call to the
   provider) or a signature-verified webhook confirms success.

2. Webhook/verification processing is IDEMPOTENT. The same event delivered
   twice (a very common provider behavior) must not double-credit a wallet,
   double-generate an invoice, or fire duplicate notifications. This is
   enforced at two layers:
     - Redis SETNX lock for fast in-flight de-duplication.
     - A unique DB constraint on payment_transactions.provider_event_id as
       the durable backstop, since Redis locks can expire/be lost.
"""
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, PaymentError
from app.core.redis import acquire_idempotency_lock
from app.core.timezone import utcnow
from app.integrations.payments import get_payment_provider
from app.models.payment import Payment
from app.models.payment_transaction import PaymentTransaction
from app.repositories.order_repository import OrderRepository
from app.services.order_service import OrderService


class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.orders = OrderRepository(db)
        self.order_service = OrderService(db)
        self.provider = get_payment_provider()

    def initialize_payment_for_order(self, *, order_id, customer_email: str, callback_url: str) -> dict:
        order = self.orders.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found.")

        result = self.provider.initialize_payment(
            order_id=str(order.id),
            amount=float(order.total_amount),
            currency=order.currency,
            customer_email=customer_email,
            callback_url=callback_url,
        )

        payment = Payment(
            order_id=order.id,
            provider=self.provider.__class__.__name__.replace("Provider", "").lower(),
            provider_reference=result.provider_reference,
            amount=order.total_amount,
            currency=order.currency,
            status="initialized",
        )
        self.db.add(payment)
        self.db.commit()

        return {"authorization_url": result.authorization_url, "provider_reference": result.provider_reference}

    def verify_and_confirm(self, provider_reference: str) -> Payment:
        """Called from the payment-callback endpoint (customer redirected
        back into the app) as a belt-and-suspenders check in addition to the
        webhook -- handles the 'webhook arrives late' edge case by letting
        the client-facing callback trigger the same verified confirmation."""
        payment = self._get_payment_by_reference(provider_reference)
        verification = self.provider.verify_payment(provider_reference)
        return self._apply_verified_result(payment, verification.status, verification.amount, verification.paid_at)

    def process_webhook(self, *, payload: bytes, signature_header: str, provider_event_id: str, event_type: str, provider_reference: str, amount: float) -> Optional[Payment]:
        if not self.provider.verify_webhook_signature(payload=payload, signature_header=signature_header):
            raise PaymentError("Webhook signature verification failed.")

        # Layer 1: fast Redis lock to short-circuit obvious duplicates
        # arriving within the same TTL window.
        if not acquire_idempotency_lock(f"payment_webhook:{provider_event_id}", ttl_seconds=3600):
            return None  # Already processed (or currently being processed) this event.

        payment = self._get_payment_by_reference(provider_reference)

        # Layer 2: durable DB-level de-duplication via unique constraint,
        # in case the Redis lock was lost/expired or this is a cold restart.
        transaction = PaymentTransaction(
            payment_id=payment.id,
            provider=payment.provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            amount=amount,
            raw_payload={"note": "raw provider payload stored verbatim in production"},
            processed=False,
        )
        try:
            self.db.add(transaction)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return None  # Duplicate event already recorded; nothing to do.

        if event_type in ("charge.success", "payment.successful"):
            payment = self._apply_verified_result(payment, "successful", amount, paid_at=None)
        elif event_type in ("charge.failed", "payment.failed"):
            payment = self._apply_verified_result(payment, "failed", amount, paid_at=None)

        transaction.processed = True
        self.db.commit()
        return payment

    def _apply_verified_result(self, payment: Payment, status: str, amount: float, paid_at) -> Payment:
        if payment.status == "successful":
            # Idempotent: already confirmed by an earlier event/verification.
            return payment

        if status == "successful":
            payment.status = "successful"
            payment.paid_at = utcnow()
            self.db.commit()

            order = self.order_service.mark_paid_from_webhook(payment.order_id)

            # Invoice generation is offloaded to a background worker so the
            # webhook/callback handler responds quickly to the provider.
            from app.workers.invoice_tasks import generate_invoice_for_order_task
            generate_invoice_for_order_task.delay(order_id=str(order.id))
        elif status == "failed":
            payment.status = "failed"
            self.db.commit()

        return payment

    def _get_payment_by_reference(self, provider_reference: str) -> Payment:
        payment = self.db.query(Payment).filter(Payment.provider_reference == provider_reference).first()
        if not payment:
            raise NotFoundError("Payment not found for the given reference.")
        return payment
