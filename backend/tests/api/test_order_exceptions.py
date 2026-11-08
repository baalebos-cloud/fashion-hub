"""Admin problem-orders list: read-only rules over stored order timestamps."""
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.timezone import utcnow
from app.main import app
from app.models.design import Design
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.professional import Professional


@pytest.fixture()
def ctx(db, make_user):
    admin, tailor, vendor, customer = make_user(role="admin"), make_user(role="tailor", full_name="Chidi Tailoring"), make_user(role="vendor", full_name="Balogun Mart"), make_user()
    pro = Professional(user_id=tailor.id, professional_type="tailor", is_verified=True)
    db.add(pro)
    db.flush()
    design = Design(professional_id=pro.id, title="Senator", base_price=Decimal(1000), is_published=True, estimated_turnaround_days=7)
    db.add(design)
    db.commit()
    now = utcnow()

    def order(kind, status, number, **times):
        buyer, seller = (customer, tailor) if kind == "customer_order" else (tailor, vendor)
        o = Order(order_number=number, order_type=kind, buyer_user_id=buyer.id, seller_user_id=seller.id, status=status,
                  subtotal=Decimal(1000), total_amount=Decimal(1000), currency="NGN", ordered_at=now - timedelta(days=30), **times)
        db.add(o)
        db.flush()
        return o

    order("customer_order", "paid", "CO-NOREPLY", paid_at=now - timedelta(hours=30))
    order("customer_order", "paid", "CO-FRESH", paid_at=now - timedelta(hours=2))
    late = order("customer_order", "in_production", "CO-LATE", paid_at=now - timedelta(days=12), accepted_at=now - timedelta(days=9))
    db.add(OrderItem(order_id=late.id, reference_type="design", reference_id=design.id, name_snapshot="Senator", unit_price=1000, quantity=1, line_total=1000))
    ontime = order("customer_order", "accepted", "CO-ONTIME", paid_at=now - timedelta(days=3), accepted_at=now - timedelta(days=2))
    db.add(OrderItem(order_id=ontime.id, reference_type="design", reference_id=design.id, name_snapshot="Senator", unit_price=1000, quantity=1, line_total=1000))
    order("customer_order", "in_production", "CO-NOESTIMATE", accepted_at=now - timedelta(days=60))
    order("vendor_order", "paid", "VO-NOCONFIRM", paid_at=now - timedelta(hours=26))
    order("vendor_order", "processing", "VO-STUCK", paid_at=now - timedelta(hours=80))
    order("vendor_order", "processing", "VO-OK", paid_at=now - timedelta(hours=10))
    order("customer_order", "completed", "CO-DONE", paid_at=now - timedelta(days=40))
    db.commit()
    current = [admin]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield dict(http=http, current=current, tailor=tailor)
    app.dependency_overrides.clear()


def test_lists_only_orders_that_broke_a_rule_oldest_first(ctx):
    res = ctx["http"].get("/api/v1/admin/order-exceptions")
    assert res.status_code == 200, res.text
    rows = res.json()
    by_number = {r["order_number"]: r for r in rows}
    assert set(by_number) == {"CO-NOREPLY", "CO-LATE", "VO-NOCONFIRM", "VO-STUCK"}
    assert by_number["CO-NOREPLY"]["kind"] == "tailor_no_reply"
    assert by_number["CO-NOREPLY"]["seller_name"] == "Chidi Tailoring"
    assert by_number["CO-LATE"]["kind"] == "overdue"
    assert "7-day estimate by 2 days" in by_number["CO-LATE"]["message"]
    assert by_number["CO-LATE"]["item"] == "Senator"
    assert by_number["VO-NOCONFIRM"]["kind"] == "vendor_no_confirm"
    assert by_number["VO-STUCK"]["kind"] == "vendor_stuck"
    assert [r["since"] for r in rows] == sorted(r["since"] for r in rows)


def test_admin_only(ctx):
    ctx["current"][0] = ctx["tailor"]
    assert ctx["http"].get("/api/v1/admin/order-exceptions").status_code == 403


def test_many_on_time_orders_do_not_hide_a_late_one(ctx, db, make_user):
    """The age test runs before the limit, so hundreds of on-time orders can't push a late one out."""
    from app.models.order import Order
    tailor, customer = ctx["tailor"], make_user()
    now = utcnow()
    db.add_all([Order(order_number=f"CO-OK{i:04d}", order_type="customer_order", buyer_user_id=customer.id, seller_user_id=tailor.id,
                      status="in_production", subtotal=Decimal(1), total_amount=Decimal(1), currency="NGN",
                      ordered_at=now - timedelta(days=90), accepted_at=now - timedelta(days=1)) for i in range(520)])
    db.add_all([Order(order_number=f"CO-PAID{i:04d}", order_type="customer_order", buyer_user_id=customer.id, seller_user_id=tailor.id,
                      status="paid", subtotal=Decimal(1), total_amount=Decimal(1), currency="NGN",
                      ordered_at=now - timedelta(days=90), paid_at=now - timedelta(hours=1)) for i in range(520)])
    db.commit()
    numbers = {r["order_number"] for r in ctx["http"].get("/api/v1/admin/order-exceptions").json()}
    assert {"CO-NOREPLY", "CO-LATE", "VO-NOCONFIRM", "VO-STUCK"} <= numbers
