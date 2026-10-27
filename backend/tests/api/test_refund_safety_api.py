"""Refund balance, authorization and fail-closed operational regressions."""
from decimal import Decimal
import uuid
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ConflictError, ForbiddenError
from app.core.timezone import utcnow
from app.main import app
from app.models.order import Order
from app.models.payment import Payment
from app.models.refund import Refund
from app.services.refund_service import RefundService


def seed_payment(db, buyer, seller):
    order = Order(
        order_number="REF-" + uuid.uuid4().hex[:16],
        buyer_user_id=buyer.id, seller_user_id=seller.id,
        order_type="customer_order", status="completed",
        subtotal=Decimal("100"), total_amount=Decimal("100"),
        currency="NGN", ordered_at=utcnow(),
    )
    db.add(order)
    db.flush()
    payment = Payment(order_id=order.id, provider=settings.PAYMENT_PROVIDER,
                      provider_reference="ps_ref_" + uuid.uuid4().hex,
                      amount=Decimal("100.00"), currency="NGN",
                      status="successful")
    db.add(payment)
    db.commit()
    return order, payment


def test_refund_balance_never_exceeds_payment(db, make_user):
    buyer, seller, stranger = make_user(), make_user(role="tailor"), make_user()
    order, payment = seed_payment(db, buyer, seller)
    service = RefundService(db)
    with pytest.raises(ForbiddenError):
        service.request_refund(order_id=order.id, requested_by=stranger,
                               amount=Decimal("10"), reason="Buyer did not request")
    first = service.request_refund(order_id=order.id, requested_by=buyer,
                                   amount=Decimal("70.00"), reason="Wrong fabric")
    assert first.status == "requested"
    with pytest.raises(ConflictError):
        service.request_refund(order_id=order.id, requested_by=buyer,
                               amount=Decimal("30.01"), reason="Wrong fabric again")
    second = service.request_refund(order_id=order.id, requested_by=buyer,
                                    amount=Decimal("30.00"), reason="Missing service")
    assert second.status == "requested"
    with pytest.raises(ConflictError):
        service.request_refund(order_id=order.id, requested_by=buyer,
                               amount=Decimal("1"), reason="Exceeds total")


def test_refund_approval_is_admin_only_and_does_not_move_funds_by_default(db, make_user, monkeypatch):
    buyer, seller, admin = make_user(), make_user(role="vendor"), make_user(role="admin")
    order, payment = seed_payment(db, buyer, seller)
    refund = RefundService(db).request_refund(
        order_id=order.id, requested_by=buyer,
        amount=Decimal("25.00"), reason="Item mismatch")
    monkeypatch.setattr(settings, "REFUND_EXECUTION_ENABLED", False)
    assert RefundService(db).approve_refund(refund.id, approved_by=admin).status == "approved"
    with pytest.raises(ConflictError):
        RefundService(db).approve_refund(refund.id, approved_by=admin)
    from app.workers.payment_tasks import process_refund_task
    assert process_refund_task(str(refund.id)) == "disabled"
    db.refresh(refund)
    assert refund.status == "approved"


def test_refund_api_scopes_customer_and_seller_views(db, make_user):
    buyer, seller, outsider, admin = (
        make_user(), make_user(role="designer"), make_user(), make_user(role="admin"))
    order, _ = seed_payment(db, buyer, seller)
    current = [buyer]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    try:
        with TestClient(app) as http:
            payload = {"order_id": str(order.id), "amount": "50.00", "reason": "Wrong measurement"}
            assert http.post("/api/v1/refunds", json=payload).status_code == 201
            assert http.get("/api/v1/refunds").status_code == 200
            assert len(http.get("/api/v1/refunds").json()) == 1
            current[0] = outsider
            assert http.get("/api/v1/refunds").json() == []
            assert http.post("/api/v1/refunds", json=payload).status_code == 403
            current[0] = seller
            assert len(http.get("/api/v1/refunds").json()) == 1
            current[0] = admin
            refunds = http.get("/api/v1/refunds").json()
            rid = refunds[0]["id"]
            assert http.post(f"/api/v1/refunds/{rid}/approve").status_code == 200
            assert http.post(f"/api/v1/refunds/{rid}/approve").status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_signed_refund_events_reconcile_only_matching_refund(db, make_user):
    buyer, seller = make_user(), make_user(role="tailor")
    order, payment = seed_payment(db, buyer, seller)
    service = RefundService(db)
    refund = service.request_refund(
        order_id=order.id, requested_by=buyer, amount=Decimal("25.00"),
        reason="Partial correction",
    )
    refund.status = "processing"
    db.commit()
    data = {"transaction_reference": payment.provider_reference, "amount": 2500,
            "currency": "NGN", "id": 1234}
    assert not service.record_paystack_event(event_type="refund.processed",
                                              payload={**data, "currency": "USD"})
    assert service.record_paystack_event(event_type="refund.pending", payload=data)
    db.refresh(refund)
    assert refund.status == "pending" and refund.provider_refund_reference == "1234"
    assert service.record_paystack_event(event_type="refund.processed", payload=data)
    db.refresh(refund)
    assert refund.status == "processed" and refund.processed_at is not None
    assert service.record_paystack_event(event_type="refund.pending", payload=data)
    db.refresh(refund)
    assert refund.status == "processed"
