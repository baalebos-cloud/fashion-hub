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
from tests.catalog_helpers import catalog_request


def _create_pending_order(db, *, customer, tailor):
    return OrderService(db).create_customer_order(**catalog_request(db, customer, tailor))


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
    from app.models.delivery import Delivery
    from app.models.delivery_partner import DeliveryPartner
    import uuid
    profile = DeliveryPartner(user_id=delivery_partner.id)
    db.add(profile)
    db.flush()
    db.add(Delivery(delivery_request_id=uuid.uuid4(), order_id=order.id,
                    delivery_partner_id=profile.id, status="assigned"))
    db.commit()
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
    request = catalog_request(db, customer, tailor, price='50.00')
    request['order_items'][0]['quantity'] = 2
    order1 = service.create_customer_order(**request)
    order2 = service.create_customer_order(**request)
    assert order1.id == order2.id



def test_customer_cannot_cancel_another_customers_order(db, make_user):
    from app.core.exceptions import ForbiddenError
    customer = make_user()
    other = make_user()
    tailor = make_user(role=UserRole.TAILOR.value)
    order = _create_pending_order(db, customer=customer, tailor=tailor)
    with pytest.raises(ForbiddenError):
        OrderService(db).cancel(order_id=order.id, actor=other)


def test_customer_cannot_mark_pending_order_paid(db, make_user):
    customer = make_user()
    tailor = make_user(role=UserRole.TAILOR.value)
    order = _create_pending_order(db, customer=customer, tailor=tailor)
    with pytest.raises(ForbiddenError):
        OrderService(db).transition(order_id=order.id, target_status=CustomerOrderStatus.PAID, actor=customer)
