"""Sandbox-only Interswitch checkout linked to the existing order ledger.

No live payment option. The production flag stays disabled, and the existing
Paystack/Flutterwave provider factory is never changed. All settlement uses
the existing atomic PaymentService reconciliation and outbox.
"""
import hashlib
import uuid
from decimal import Decimal
from urllib.parse import urlsplit

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, PaymentError
from app.integrations.payments.base import VerifyPaymentResult
from app.integrations.payments.interswitch_checkout import (
    CheckoutForm, build_checkout_form, requery_transaction,
)
from app.models.payment import Payment
from app.services.payment_service import PaymentService


class InterswitchSandboxService(PaymentService):
    """Isolated sandbox checkout; no provider factory or live behavior change."""

    @staticmethod
    def _live_mode() -> bool:
        return False

    @staticmethod
    def _require_sandbox():
        if (settings.is_production or not settings.INTERSWITCH_SANDBOX_ENABLED
                or not settings.INTERSWITCH_MERCHANT_CODE
                or not settings.INTERSWITCH_PAY_ITEM_ID):
            raise ConflictError("Interswitch sandbox checkout is not configured.")

    @staticmethod
    def _assert_provider(payment):
        if payment.provider != "interswitch":
            raise PaymentError("Payment provider does not match Interswitch.")

    @staticmethod
    def _return_url() -> str:
        url = f"{settings.APP_URL.rstrip('/')}{settings.API_PREFIX}/interswitch/return"
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ConflictError("A public HTTPS backend callback URL is required.")
        return url

    def _checkout_form(self, payment, email: str) -> CheckoutForm:
        return build_checkout_form(
            merchant_code=settings.INTERSWITCH_MERCHANT_CODE,
            pay_item_id=settings.INTERSWITCH_PAY_ITEM_ID,
            reference=payment.provider_reference, amount=payment.amount,
            customer_email=email, return_url=self._return_url(), live=self._live_mode(),
        )

    def initialize_checkout(self, *, order_id, buyer_user_id, customer_email: str) -> CheckoutForm:
        self._require_sandbox()
        order = self.orders.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found.")
        if str(order.buyer_user_id) != str(buyer_user_id):
            raise ForbiddenError("Only the order buyer may initialize payment.")
        order = self.orders.get_by_id_for_update(order_id)
        if (order.status not in {"pending", "checkout", "payment_pending"}
                or order.total_amount <= 0 or order.currency != "NGN"):
            raise ConflictError("Order is not payable through Interswitch.")
        from app.services.catalog_order_service import assert_catalog_order_payable
        assert_catalog_order_payable(order)
        # Scope the proof of concept to customer fashion orders. Vendor
        # material-order redirects require a separate, role-specific flow.
        if order.order_type != "customer_order":
            raise ConflictError("Sandbox currently supports customer fashion orders only.")
        existing = self.db.query(Payment).filter(Payment.order_id == order.id).first()
        if existing:
            self._assert_provider(existing)
            if existing.status not in {"initialized", "pending"}:
                raise ConflictError("The order already has a completed payment attempt.")
            return self._checkout_form(existing, customer_email)
        reference = "seam_" + uuid.uuid4().hex
        payment = Payment(
            order_id=order.id, provider="interswitch", provider_reference=reference,
            amount=order.total_amount, currency="NGN", status="initialized",
        )
        # Construct and validate the hosted form before committing a payment.
        checkout_form = self._checkout_form(payment, customer_email)
        try:
            self.db.add(payment)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return checkout_form

    def verify_and_confirm(self, provider_reference: str, *, buyer_user_id=None) -> Payment:
        self._require_sandbox()
        payment = self._get_payment_by_reference(provider_reference)
        self._assert_provider(payment)
        order = self.orders.get_by_id(payment.order_id)
        if not order:
            raise NotFoundError("Order not found.")
        if buyer_user_id is None or str(order.buyer_user_id) != str(buyer_user_id):
            raise ForbiddenError("Only the order buyer may verify this payment.")
        result = requery_transaction(
            merchant_code=settings.INTERSWITCH_MERCHANT_CODE,
            reference=provider_reference, expected_amount=payment.amount,
            live=self._live_mode(),
        )
        verification = VerifyPaymentResult(
            provider_reference=result.reference,
            status="successful" if result.successful else "pending",
            amount=Decimal(result.amount_minor) / Decimal("100"),
            currency=result.currency, paid_at=None, raw_response={},
        )
        self._validate_verification(payment, verification)
        event_id = "verify:" + hashlib.sha256(
            f"interswitch:{provider_reference}:{verification.status}".encode()
        ).hexdigest()
        settled = self._settle(provider_reference, verification, event_id,
                               "payment.verified", buyer_user_id)
        return settled if settled is not None else self._get_payment_by_reference(provider_reference)
