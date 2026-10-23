"""Database-backed regression tests for persisted reviews and vendor ownership."""
from decimal import Decimal
import uuid

from fastapi.testclient import TestClient
import pytest
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ConflictError, ForbiddenError, InvalidStateTransitionError
from app.main import app
from app.models.order import Order
from app.models.professional import Professional
from app.models.rating import Rating
from app.models.review import Review
from app.services.order_service import OrderService
from app.services.review_service import ReviewService
from app.services.vendor_fulfillment_service import VendorFulfillmentService
from tests.catalog_helpers import catalog_request


def test_review_persisted_once_and_aggregate_updated(db, make_user):
    customer, tailor = make_user(), make_user(role="tailor")
    order = OrderService(db).create_customer_order(**catalog_request(db, customer, tailor))
    order.status = "completed"
    db.commit()
    review = ReviewService(db).create_review(order=order, reviewer=customer, score=4, comment="Excellent")
    assert db.query(Review).filter_by(order_id=order.id).count() == 1
    assert db.query(Rating).filter_by(review_id=review.id).one().score == 4
    profile = db.query(Professional).filter_by(user_id=tailor.id).one()
    assert profile.review_count == 1 and profile.average_rating == Decimal("4.00")
    with pytest.raises(ConflictError):
        ReviewService(db).create_review(order=order, reviewer=customer, score=5, comment=None)
    with pytest.raises(ForbiddenError):
        ReviewService(db).create_review(order=order, reviewer=make_user(), score=5, comment=None)


def test_review_http_validates_rating_and_identity(db, make_user):
    customer, tailor, stranger = make_user(), make_user(role="tailor"), make_user()
    order = OrderService(db).create_customer_order(**catalog_request(db, customer, tailor))
    order.status = "completed"
    db.commit()
    current = [stranger]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    try:
        with TestClient(app) as client:
            endpoint = f"/api/v1/orders/{order.id}/review"
            assert client.post(endpoint, json={"score": 5}).status_code == 403
            current[0] = customer
            assert client.post(endpoint, json={"score": 10}).status_code == 422
            created = client.post(endpoint, json={"score": 5, "comment": "Perfect"})
            assert created.status_code == 201, created.text
            assert created.json()["score"] == 5
            profile = db.query(Professional).filter_by(user_id=tailor.id).one()
            public = client.get("/api/v1/reviews", params={"professional_id": str(profile.id)})
            assert public.status_code == 200 and public.json()[0]["score"] == 5
            assert client.post(endpoint, json={"score": 5}).status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_vendor_fulfillment_requires_owning_vendor_and_sequence(db, make_user):
    buyer, vendor, other = make_user(role="tailor"), make_user(role="vendor"), make_user(role="vendor")
    order = Order(order_number="VH-" + uuid.uuid4().hex[:20], order_type="vendor_order",
                  buyer_user_id=buyer.id, seller_user_id=vendor.id, status="paid",
                  subtotal=Decimal("100.00"), total_amount=Decimal("100.00"), currency="NGN")
    db.add(order)
    db.commit()
    service = VendorFulfillmentService(db)
    with pytest.raises(ForbiddenError):
        service.transition(order_id=order.id, actor=other, target_status="confirmed")
    with pytest.raises(InvalidStateTransitionError):
        service.transition(order_id=order.id, actor=vendor, target_status="ready_for_pickup")
    for target in ("confirmed", "processing", "ready_for_pickup"):
        assert service.transition(order_id=order.id, actor=vendor, target_status=target).status == target
    with pytest.raises(InvalidStateTransitionError):
        service.transition(order_id=order.id, actor=vendor, target_status="confirmed")
