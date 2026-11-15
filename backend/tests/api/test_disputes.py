"""Disputes: the buyer opens one on a paid order, the seller's payout is held, an admin resolves it."""
import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.core.timezone import utcnow
from app.main import app
from app.models.dispute import Dispute
from app.models.notification import Notification
from app.models.order import Order
from app.models.payout import Payout
from app.services.payout_release_service import PayoutReleaseService

CURRENT = []


@pytest.fixture()
def client(db):
    def override_db():
        yield db
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: CURRENT[-1]
    limiter.reset()
    with TestClient(app) as http:
        yield http
    app.dependency_overrides.clear()
    CURRENT.clear()


def as_(user):
    CURRENT.append(user)
    return user


@pytest.fixture()
def world(db, make_user):
    customer, tailor, admin = make_user(role="customer"), make_user(role="tailor"), make_user(role="admin")
    order = Order(order_number="CO-" + uuid.uuid4().hex[:8], order_type="customer_order", buyer_user_id=customer.id,
                  seller_user_id=tailor.id, status="delivered", subtotal=Decimal("50000"), total_amount=Decimal("50000"),
                  currency="NGN", ordered_at=utcnow())
    db.add(order); db.commit()
    return customer, tailor, admin, order


def open_(client, order, reason="wrong_size", text="The trousers are 5cm too short."):
    return client.post("/api/v1/disputes", json={"order_id": str(order.id), "reason": reason, "description": text})


def test_buyer_opens_a_dispute_and_the_seller_is_told(client, db, world):
    customer, tailor, _, order = world
    as_(customer)
    r = open_(client, order)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "open" and r.json()["reason_label"] == "Wrong size or fit"
    assert db.query(Notification).filter_by(recipient_user_id=tailor.id, event_type="order.dispute").count() == 1
    as_(tailor)  # the seller sees it on their order
    mine = client.get(f"/api/v1/disputes/mine?order_id={order.id}").json()
    assert len(mine) == 1 and mine[0]["description"].startswith("The trousers")


def test_only_one_open_dispute_and_only_the_buyer(client, db, world, make_user):
    customer, tailor, _, order = world
    as_(make_user(role="customer"))
    assert open_(client, order).status_code == 404
    as_(tailor)
    assert open_(client, order).status_code == 404
    as_(customer)
    assert open_(client, order).status_code == 201
    assert open_(client, order).status_code == 409


@pytest.mark.parametrize("status", ["pending", "cancelled", "refunded"])
def test_unpaid_or_closed_orders_cannot_be_disputed(client, db, world, status):
    customer, _, _, order = world
    order.status = status; db.commit()
    as_(customer)
    assert open_(client, order).status_code == 409


def test_open_dispute_holds_the_sellers_payout(client, db, world):
    customer, tailor, _, order = world
    as_(customer)
    open_(client, order)
    payout = Payout(order_id=order.id, seller_user_id=tailor.id, gross_amount=Decimal("50000"),
                    commission_rate=Decimal("0.10"), commission_amount=Decimal("5000"), net_amount=Decimal("45000"),
                    currency="NGN", status="pending")
    db.add(payout); db.commit()
    assert "dispute" in PayoutReleaseService(db).blocker(payout, order)


def test_admin_resolves_without_money_and_both_sides_hear(client, db, world):
    customer, tailor, admin, order = world
    as_(customer)
    dispute_id = open_(client, order).json()["id"]
    as_(admin)
    listed = client.get("/api/v1/admin/disputes?status=open").json()
    assert listed["total"] == 1 and listed["items"][0]["buyer_name"] == customer.full_name
    r = client.post(f"/api/v1/admin/disputes/{dispute_id}/resolve",
                    json={"outcome": "remake", "note": "Tailor will alter the trousers free of charge."})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "resolved" and r.json()["outcome_label"] == "Remake or alteration"
    assert db.query(Notification).filter_by(event_type="order.dispute", title="Your dispute was resolved").count() == 1
    again = client.post(f"/api/v1/admin/disputes/{dispute_id}/resolve", json={"outcome": "no_action", "note": "again please"})
    assert again.status_code == 409


def test_refund_outcome_needs_an_authenticator_code(client, db, world):
    customer, _, admin, order = world
    as_(customer)
    dispute_id = open_(client, order).json()["id"]
    as_(admin)
    r = client.post(f"/api/v1/admin/disputes/{dispute_id}/resolve",
                    json={"outcome": "refund", "note": "Not delivered; refunding in full.", "refund_amount": "50000"})
    assert r.status_code == 403 and db.get(Dispute, uuid.UUID(dispute_id)).status == "open"


def test_refund_outcome_goes_through_the_refund_service(client, db, world):
    customer, _, admin, order = world
    as_(customer)
    dispute_id = open_(client, order).json()["id"]
    as_(admin)
    refund = type("R", (), {"id": uuid.uuid4(), "status": "requested"})()
    approved = type("R", (), {"id": refund.id, "status": "approved"})()
    with patch("app.services.admin_auth_service.AdminStepUpService.require"), \
         patch("app.services.refund_service.RefundService.request_refund", return_value=refund) as req, \
         patch("app.services.refund_service.RefundService.approve_refund", return_value=approved) as ok:
        too_much = client.post(f"/api/v1/admin/disputes/{dispute_id}/resolve",
                               json={"outcome": "refund", "note": "Refund please", "refund_amount": "60000"})
        assert too_much.status_code == 422
        r = client.post(f"/api/v1/admin/disputes/{dispute_id}/resolve",
                        json={"outcome": "refund", "note": "Not delivered; refunding in full.", "refund_amount": "50000"})
    assert r.status_code == 200, r.text
    assert req.call_args.kwargs["amount"] == Decimal("50000") and req.call_args.kwargs["idempotency_key"] == f"dispute-{dispute_id}"
    ok.assert_called_once()
    d = db.get(Dispute, uuid.UUID(dispute_id))
    assert d.status == "resolved" and d.refund_id == refund.id and d.refund_amount == Decimal("50000")


def test_customers_cannot_resolve(client, world):
    customer, *_ , order = world
    as_(customer)
    dispute_id = open_(client, order).json()["id"]
    assert client.post(f"/api/v1/admin/disputes/{dispute_id}/resolve",
                       json={"outcome": "no_action", "note": "I decide myself"}).status_code == 403


def test_a_refund_in_progress_blocks_other_decisions(client, db, world, make_user):
    customer, tailor, admin, order = world
    as_(customer)
    dispute_id = open_(client, order).json()["id"]
    d = db.get(Dispute, uuid.UUID(dispute_id))
    d.status, d.resolved_by_user_id = "resolving", admin.id  # admin 1 is part-way through a refund
    db.commit()
    as_(make_user(role="admin"))
    other = client.post(f"/api/v1/admin/disputes/{dispute_id}/resolve", json={"outcome": "no_action", "note": "Not upheld, sorry"})
    assert other.status_code == 409 and "Another admin" in other.text
    as_(admin)
    switch = client.post(f"/api/v1/admin/disputes/{dispute_id}/resolve", json={"outcome": "remake", "note": "Remake instead"})
    assert switch.status_code == 409
    # Still counts as open: no second dispute, and the payout stays held.
    as_(customer)
    assert open_(client, order).status_code == 409
    payout = Payout(order_id=order.id, seller_user_id=tailor.id, gross_amount=Decimal("50000"), commission_rate=Decimal("0.10"),
                    commission_amount=Decimal("5000"), net_amount=Decimal("45000"), currency="NGN", status="pending")
    db.add(payout); db.commit()
    assert "dispute" in PayoutReleaseService(db).blocker(payout, order)


def test_a_failed_refund_reopens_the_dispute(client, db, world):
    from app.core.exceptions import ConflictError
    customer, _, admin, order = world
    as_(customer)
    dispute_id = open_(client, order).json()["id"]
    as_(admin)
    with patch("app.services.admin_auth_service.AdminStepUpService.require"), \
         patch("app.services.refund_service.RefundService.request_refund",
               side_effect=ConflictError("Only settled payments are refundable.")):
        r = client.post(f"/api/v1/admin/disputes/{dispute_id}/resolve",
                        json={"outcome": "refund", "note": "Refunding in full.", "refund_amount": "50000"})
    assert r.status_code == 409 and "settled" in r.text
    db.expire_all()
    d = db.get(Dispute, uuid.UUID(dispute_id))
    assert d.status == "open" and d.resolved_by_user_id is None
