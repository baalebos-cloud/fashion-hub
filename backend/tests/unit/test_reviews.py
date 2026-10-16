"""Unit tests: a review can only be created after RECEIVED/COMPLETED."""
import pytest

from app.core.constants import CustomerOrderStatus, UserRole
from app.core.exceptions import ConflictError
from app.services.order_service import OrderService
from tests.catalog_helpers import catalog_request
from app.services.review_service import ReviewService


def test_cannot_review_before_order_received(db, make_user):
    customer = make_user(role=UserRole.CUSTOMER.value)
    tailor = make_user(role=UserRole.TAILOR.value)
    order_service = OrderService(db)
    order = order_service.create_customer_order(**catalog_request(db, customer, tailor, price='75.00'))

    review_service = ReviewService(db)
    with pytest.raises(ConflictError):
        review_service.create_review(order=order, reviewer=customer, comment="Great!", score=5)
