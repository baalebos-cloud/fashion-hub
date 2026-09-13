"""Unit tests: a review can only be created after RECEIVED/COMPLETED."""
import pytest

from app.core.constants import CustomerOrderStatus, UserRole
from app.core.exceptions import ConflictError
from app.services.order_service import OrderService
from app.services.review_service import ReviewService


def test_cannot_review_before_order_received(db, make_user):
    customer = make_user(role=UserRole.CUSTOMER.value)
    tailor = make_user(role=UserRole.TAILOR.value)
    order_service = OrderService(db)
    order = order_service.create_customer_order(
        customer=customer,
        professional_user_id=tailor.id,
        order_items=[{"unit_price": 75.0, "quantity": 1}],
        delivery_address_id=None,
        measurement_profile_id=None,
        idempotency_key=None,
    )

    review_service = ReviewService(db)
    with pytest.raises(ConflictError):
        review_service.create_review(order=order, reviewer=customer, comment="Great!", score=5)
