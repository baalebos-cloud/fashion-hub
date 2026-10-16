"""
Unit tests for PaymentService, focused on the payment edge cases called out
in the project spec: duplicate webhook delivery and late webhook arrival.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.core.constants import UserRole
from app.models.payment import Payment
from app.services.order_service import OrderService
from tests.catalog_helpers import catalog_request
from app.services.payment_service import PaymentService
from app.integrations.payments.base import VerifyPaymentResult


def _make_order_and_payment(db, make_user):
    customer = make_user(role=UserRole.CUSTOMER.value)
    tailor = make_user(role=UserRole.TAILOR.value)
    order_service = OrderService(db)
    order = order_service.create_customer_order(**catalog_request(db, customer, tailor, price='200.00'))
    payment = Payment(
        order_id=order.id,
        provider="paystack",
        provider_reference="ref-123",
        amount=order.total_amount,
        currency=order.currency,
        status="initialized",
    )
    db.add(payment)
    db.commit()
    return order, payment


@patch("app.services.payment_service.get_payment_provider")
def test_duplicate_webhook_is_processed_only_once(mock_get_provider, db, make_user):
    provider = MagicMock()
    provider.verify_webhook_signature.return_value = True
    provider.__class__.__name__ = "PaystackProvider"
    mock_get_provider.return_value = provider

    order, payment = _make_order_and_payment(db, make_user)
    provider.verify_payment.return_value = VerifyPaymentResult(
        provider_reference=payment.provider_reference, status="successful",
        amount=float(payment.amount), currency=payment.currency, paid_at=None, raw_response={},
    )
    service = PaymentService(db)

    kwargs = dict(
        payload=b"raw-body",
        signature_header="valid-signature",
        provider_event_id="evt-abc-123",
        event_type="charge.success",
        provider_reference=payment.provider_reference,
        amount=float(payment.amount),
    )

    first_result = service.process_webhook(**kwargs)
    assert first_result is not None
    assert first_result.status == "successful"

    # Same event delivered again (very common provider behavior) must be a
    # no-op: no duplicate invoice generation, no re-transition of the order.
    second_result = service.process_webhook(**kwargs)
    assert second_result is None


@patch("app.services.payment_service.get_payment_provider")
def test_failed_webhook_signature_is_rejected(mock_get_provider, db, make_user):
    from app.core.exceptions import PaymentError

    provider = MagicMock()
    provider.verify_webhook_signature.return_value = False
    mock_get_provider.return_value = provider

    order, payment = _make_order_and_payment(db, make_user)
    service = PaymentService(db)

    with pytest.raises(PaymentError):
        service.process_webhook(
            payload=b"raw-body",
            signature_header="bad-signature",
            provider_event_id="evt-xyz",
            event_type="charge.success",
            provider_reference=payment.provider_reference,
            amount=float(payment.amount),
        )


def test_payment_initialization_rejects_another_buyer():
    from app.core.exceptions import ForbiddenError
    with patch('app.services.payment_service.get_payment_provider') as get_provider:
        service = PaymentService(MagicMock())
        service.orders.get_by_id = MagicMock(return_value=MagicMock(buyer_user_id='actual-buyer'))
        with pytest.raises(ForbiddenError):
            service.initialize_payment_for_order(order_id='order-id', customer_email='other@example.com',
                                                 callback_url='https://example.com', buyer_user_id='another-buyer')
        get_provider.return_value.initialize_payment.assert_not_called()


def test_payment_verification_rejects_another_buyer():
    from app.core.exceptions import ForbiddenError
    with patch('app.services.payment_service.get_payment_provider') as get_provider:
        service = PaymentService(MagicMock())
        service._get_payment_by_reference = MagicMock(return_value=MagicMock(order_id='order-id'))
        service.orders.get_by_id = MagicMock(return_value=MagicMock(buyer_user_id='actual-buyer'))
        with pytest.raises(ForbiddenError):
            service.verify_and_confirm('reference', buyer_user_id='another-buyer')
        get_provider.return_value.verify_payment.assert_not_called()
