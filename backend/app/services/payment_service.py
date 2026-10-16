"""Provider verification outside locks; settlement and durable work in one commit.

This service owns its Session's transaction boundary. Callers must not attach
unrelated pending writes. It never publishes a Celery task while settling funds.
"""
import hashlib
from typing import Optional
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, PaymentError
from app.core.policies import validate_payment_identity
from app.core.timezone import utcnow
from app.integrations.payments import get_payment_provider
from app.models.audit_log import AuditLog
from app.models.payment import Payment
from app.models.payment_outbox import PaymentOutbox
from app.models.payment_transaction import PaymentTransaction
from app.repositories.order_repository import OrderRepository
from app.services.order_service import OrderService
from app.services.payout_service import PayoutService
from app.services.referral_service import ReferralService

PAID_CUSTOMER_STATES = {"paid", "accepted", "in_production", "ready_for_delivery", "shipped",
                        "out_for_delivery", "delivered", "received", "completed"}
PAID_VENDOR_STATES = {"paid", "confirmed", "processing", "ready_for_pickup", "picked_up",
                     "in_transit", "delivered", "received", "completed"}


class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.orders = OrderRepository(db)
        self.order_service = OrderService(db)
        self.provider = get_payment_provider()

    def initialize_payment_for_order(self, *, order_id, customer_email: str, callback_url: str, buyer_user_id) -> dict:
        order = self.orders.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found.")
        if str(order.buyer_user_id) != str(buyer_user_id):
            raise ForbiddenError("Only the buyer may initialize this payment.")
        order = self.orders.get_by_id_for_update(order_id)
        if order.status not in {"pending", "checkout", "payment_pending"} or order.total_amount <= 0:
            raise ConflictError("Order is not payable.")
        from app.services.catalog_order_service import assert_catalog_order_payable
        assert_catalog_order_payable(order)
        try:
            callback = urlsplit(callback_url)
            origin = f"{callback.scheme}://{callback.netloc}"
            allowed = {value.rstrip('/') for value in settings.CORS_ALLOWED_ORIGINS}
            if callback.scheme not in {'http', 'https'} or callback.username or callback.password or origin not in allowed or len(callback_url) > 2048:
                raise ValueError('Untrusted callback origin')
        except ValueError as exc:
            from app.core.exceptions import ValidationAppError
            raise ValidationAppError('Payment callback must use a configured application origin.') from exc
        existing = self.db.query(Payment).filter(Payment.order_id == order.id).first()
        if existing:
            if existing.status in {'initialized', 'pending'} and existing.authorization_url:
                return {'authorization_url': existing.authorization_url, 'provider_reference': existing.provider_reference}
            raise ConflictError("This order already has a payment. Verify the existing reference.")
        result = self.provider.initialize_payment(
            order_id=str(order.id), amount=float(order.total_amount), currency=order.currency,
            customer_email=customer_email, callback_url=callback_url,
        )
        if not result.authorization_url or len(result.authorization_url) > 2048 or urlsplit(result.authorization_url).scheme != 'https':
            raise PaymentError('Provider did not return a secure authorization URL.')
        try:
            self.db.add(Payment(
                order_id=order.id, provider=settings.PAYMENT_PROVIDER,
                provider_reference=result.provider_reference, amount=order.total_amount,
                currency=order.currency, status="initialized", authorization_url=result.authorization_url,
            ))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return {"authorization_url": result.authorization_url, "provider_reference": result.provider_reference}

    def verify_and_confirm(self, provider_reference: str, *, buyer_user_id=None) -> Payment:
        payment = self._get_payment_by_reference(provider_reference)
        if buyer_user_id is not None:
            order = self.orders.get_by_id(payment.order_id)
            if not order or str(order.buyer_user_id) != str(buyer_user_id):
                raise ForbiddenError("Only the buyer may verify this payment.")
        self._assert_provider(payment)
        verification = self.provider.verify_payment(provider_reference)
        self._validate_verification(payment, verification)
        event_id = "verify:" + hashlib.sha256(
            f"{payment.provider}:{provider_reference}:{verification.status}".encode()
        ).hexdigest()
        settled = self._settle(provider_reference, verification, event_id, "payment.verified", buyer_user_id)
        return settled if settled is not None else self._get_payment_by_reference(provider_reference)

    def process_webhook(self, *, payload: bytes, signature_header: str, provider_event_id: str,
                        event_type: str, provider_reference: str, amount) -> Optional[Payment]:
        if not self.provider.verify_webhook_signature(payload=payload, signature_header=signature_header):
            raise PaymentError("Webhook signature verification failed.")
        if not provider_event_id or len(provider_event_id) > 128:
            raise PaymentError("Invalid provider event ID.")
        if event_type not in {"charge.success", "charge.failed", "payment.successful", "payment.failed"}:
            raise PaymentError("Unsupported payment event.")
        payment = self._get_payment_by_reference(provider_reference)
        self._assert_provider(payment)
        previous = self._event(provider_event_id, payment)
        if previous and previous.processed:
            self.db.commit()  # completed events are immutable; no provider dependency on retries
            return None
        verification = self.provider.verify_payment(provider_reference)
        self._validate_verification(payment, verification)
        if event_type in {"charge.success", "payment.successful"} and verification.status != "successful":
            raise PaymentError("Provider has not confirmed successful settlement.")
        # Event amounts are never used to credit funds; only the provider's
        # independently verified amount/currency/reference can do that.
        return self._settle(provider_reference, verification, provider_event_id, event_type)

    def _settle(self, reference, verification, event_id, event_type, buyer_user_id=None):
        try:
            payment = (self.db.query(Payment).filter(Payment.provider_reference == reference)
                       .with_for_update().populate_existing().first())
            if not payment:
                raise NotFoundError("Payment not found.")
            self._assert_provider(payment)
            self._validate_verification(payment, verification)
            transaction = self._event(event_id, payment)
            if transaction and transaction.processed:
                self.db.commit()
                return None
            order = self.orders.get_by_id_for_update(payment.order_id)
            if not order:
                raise NotFoundError("Order not found.")
            if buyer_user_id is not None and str(order.buyer_user_id) != str(buyer_user_id):
                raise ForbiddenError("Only the buyer may verify this payment.")
            if not transaction:
                transaction = PaymentTransaction(payment_id=payment.id, provider=payment.provider,
                                                 provider_event_id=event_id, event_type=event_type)
                self.db.add(transaction)
            transaction.amount = verification.amount
            # Store reconciliation facts, not raw customer/provider identity data.
            transaction.raw_payload = {"verified_status": verification.status,
                                       "currency": verification.currency, "reference": reference}
            transaction.processed = False
            self._apply_verified_result(payment, order, verification)
            transaction.processed = True
            self.db.commit()
            return payment
        except Exception:
            self.db.rollback()
            raise

    def _apply_verified_result(self, payment, order, verification):
        if payment.status == "reversed":
            return  # a late delivery cannot undo an already recorded reversal
        if verification.status != "successful":
            if payment.status != "successful":
                payment.status = verification.status
            return
        payment.status = "successful"
        payment.paid_at = payment.paid_at or utcnow()
        prior_work = self.db.query(PaymentOutbox).filter(PaymentOutbox.payment_id == payment.id).first()
        if prior_work:
            return  # financial work and this outbox row were committed together

        # A payment can arrive after cancellation. Record the funds and a
        # durable review signal, without reviving the order or paying the seller.
        valid_states = PAID_CUSTOMER_STATES if order.order_type == "customer_order" else PAID_VENDOR_STATES
        payable = {"pending"} if order.order_type == "customer_order" else {"checkout", "payment_pending"}
        if order.status not in valid_states | payable:
            self.db.add(AuditLog(action="payment.review_required", resource_type="payment",
                                 resource_id=payment.id,
                                 metadata_json={"order_id": str(order.id), "order_status": order.status}))
            self._enqueue(payment, "payment.review", {"order_id": str(order.id)})
            return

        order = self.order_service.mark_paid_from_webhook(order.id, commit=False)
        PayoutService(self.db).create_for_order(order, commit=False)
        referral = ReferralService(self.db).qualify_if_applicable(
            referred_user_id=order.buyer_user_id, qualifying_order_id=order.id,
            order_total=order.total_amount, currency=order.currency, commit=False,
        )
        self._enqueue(payment, "payment.settled", {
            "order_id": str(order.id), "referral_id": str(referral.id) if referral else None,
        })

    def _enqueue(self, payment, kind, payload):
        self.db.add(PaymentOutbox(payment_id=payment.id, dedupe_key=f"{kind}:{payment.id}",
                                  kind=kind, payload=payload))

    def _event(self, event_id, payment):
        event = self.db.query(PaymentTransaction).filter(PaymentTransaction.provider_event_id == event_id).first()
        if event and (event.payment_id != payment.id or event.provider != payment.provider):
            raise ConflictError("Provider event ID is already associated with a different payment.")
        return event

    def _get_payment_by_reference(self, provider_reference: str) -> Payment:
        payment = self.db.query(Payment).filter(Payment.provider_reference == provider_reference).first()
        if not payment:
            raise NotFoundError("Payment not found for the given reference.")
        return payment

    @staticmethod
    def _assert_provider(payment):
        if payment.provider != settings.PAYMENT_PROVIDER:
            raise PaymentError("Payment provider does not match the configured provider.")

    @staticmethod
    def _validate_verification(payment, verification):
        if verification.status not in {"successful", "pending", "failed"}:
            raise PaymentError("Unsupported provider payment status.")
        try:
            validate_payment_identity(
                expected_reference=payment.provider_reference, reference=verification.provider_reference,
                expected_amount=payment.amount, amount=verification.amount,
                expected_currency=payment.currency, currency=verification.currency,
            )
        except ValueError as exc:
            raise PaymentError(str(exc)) from exc
