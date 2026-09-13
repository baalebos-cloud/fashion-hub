"""
Unit tests for OrderService -- the authoritative order state machine.

Covers the explicit product requirements:
  - A tailor cannot mark an order as RECEIVED.
  - Only the order's own customer can mark it as RECEIVED.
  - Invalid transitions (e.g. skipping PENDING -> RECEIVED) are rejected.
  - A tailor cannot modify another tailor's order.
"""
import pytest

from app.core.constants import CustomerOrderStatus, UserRole
from app.core.exceptions import ForbiddenError, InvalidStateTransitionError
from app.services.order_service import OrderService


def _create_pending_order(db, *, customer, tailor):
    service = OrderService(db)
    return service.create_customer_order(
        customer=customer,
        professional_user_id=tailor.id,
        order_items=[{"unit_price": 100.0, "quantity": 1}],
        delivery_address_id=None,
        measurement_profile_id=None,
        idempotency_key=None,
    )


def test_tailor_cannot_mark_order_received(db, make_user):
    customer = make_user(role=UserRole.CUSTOMER.value)
    tailor = make_user(role=UserRole.TAILOR.value)
    order = _create_pending_order(db, customer=customer, tailor=tailor)

    service = OrderService(db)
    # Fast-forward order to DELIVERED via the legitimate path.
    order = service.mark_paid_from_webhook(order.id)
    order = service.transition(order_id=order.id, target_status=CustomerOrderStatus.ACCEPTED, actor=tailor)
    order = service.transition(order_id=order.id, target_status=CustomerOrderStatus.IN_PRODUCTION, actor=tailor)
    order = service.transition(order_id=order.id, target_status=CustomerOrderStatus.READY_FOR_DELIVERY, actor=tailor)
    order = service.transition(order_id=order.id, target_status=CustomerOrderStatus.SHIPPED, actor=tailor)

    delivery_partner = make_user(role=UserRole.DELIVERY_PARTNER.value)
    order = service.transition(order_id=order.id, target_status=CustomerOrderStatus.OUT_FOR_DELIVERY, actor=delivery_partner)
    order = service.transition(order_id=order.id, target_status=CustomerOrderStatus.DELIVERED, actor=delivery_partner)

    with pytest.raises(ForbiddenError):
        service.transition(order_id=order.id, target_status=CustomerOrderStatus.RECEIVED, actor=tailor)


def test_only_the_orders_own_customer_can_mark_received(db, make_user):
    customer = make_user(role=UserRole.CUSTOMER.value)
    other_customer = make_user(role=UserRole.CUSTOMER.value)
    tailor = make_user(role=UserRole.TAILOR.value)
    order = _create_pending_order(db, customer=customer, tailor=tailor)

    service = OrderService(db)
    order = service.mark_paid_from_webhook(order.id)
    order.status = CustomerOrderStatus.DELIVERED.value  # shortcut for test setup
    db.commit()

    with pytest.raises(ForbiddenError):
        service.transition(order_id=order.id, target_status=CustomerOrderStatus.RECEIVED, actor=other_customer)

    # The real customer succeeds.
    result = service.transition(order_id=order.id, target_status=CustomerOrderStatus.RECEIVED, actor=customer)
    assert result.status == CustomerOrderStatus.RECEIVED.value
    assert result.received_at is not None


def test_cannot_skip_states(db, make_user):
    customer = make_user(role=UserRole.CUSTOMER.value)
    tailor = make_user(role=UserRole.TAILOR.value)
    order = _create_pending_order(db, customer=customer, tailor=tailor)

    service = OrderService(db)
    with pytest.raises(InvalidStateTransitionError):
        # Order is still PENDING; cannot jump straight to RECEIVED.
        service.transition(order_id=order.id, target_status=CustomerOrderStatus.RECEIVED, actor=customer)


def test_tailor_cannot_modify_another_tailors_order(db, make_user):
    customer = make_user(role=UserRole.CUSTOMER.value)
    tailor = make_user(role=UserRole.TAILOR.value)
    other_tailor = make_user(role=UserRole.TAILOR.value)
    order = _create_pending_order(db, customer=customer, tailor=tailor)

    service = OrderService(db)
    service.mark_paid_from_webhook(order.id)

    with pytest.raises(ForbiddenError):
        service.transition(order_id=order.id, target_status=CustomerOrderStatus.ACCEPTED, actor=other_tailor)


def test_duplicate_order_submission_is_idempotent(db, make_user):
    customer = make_user(role=UserRole.CUSTOMER.value)
    tailor = make_user(role=UserRole.TAILOR.value)

    service = OrderService(db)
    key = "client-generated-idempotency-key-123"
    order1 = service.create_customer_order(
        customer=customer,
        professional_user_id=tailor.id,
        order_items=[{"unit_price": 50.0, "quantity": 2}],
        delivery_address_id=None,
        measurement_profile_id=None,
        idempotency_key=key,
    )
    order2 = service.create_customer_order(
        customer=customer,
        professional_user_id=tailor.id,
        order_items=[{"unit_price": 50.0, "quantity": 2}],
        delivery_address_id=None,
        measurement_profile_id=None,
        idempotency_key=key,
    )
    assert order1.id == order2.id
