"""
Unit tests for PaymentService, focused on the payment edge cases called out
in the project spec: duplicate webhook delivery and late webhook arrival.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.core.constants import UserRole
from app.models.payment import Payment
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService


def _make_order_and_payment(db, make_user):
    customer = make_user(role=UserRole.CUSTOMER.value)
    tailor = make_user(role=UserRole.TAILOR.value)
    order_service = OrderService(db)
    order = order_service.create_customer_order(
        customer=customer,
        professional_user_id=tailor.id,
        order_items=[{"unit_price": 200.0, "quantity": 1}],
        delivery_address_id=None,
        measurement_profile_id=None,
        idempotency_key=None,
    )
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
