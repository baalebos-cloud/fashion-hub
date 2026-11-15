"""Admin lists (vendors, riders, payments, invoices, reviews), Reports, and the Favorites list."""
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.dependencies import get_current_user
from app.core.timezone import utcnow
from app.main import app
from app.models.delivery_partner import DeliveryPartner
from app.models.favorite import Favorite
from app.models.invoice import Invoice
from app.models.order import Order
from app.models.payment import Payment
from app.models.professional import Professional
from app.models.rating import Rating
from app.models.review import Review
from tests.vendor_helpers import catalog


CURRENT = []


@pytest.fixture()
def client(db):
    def override_db():
        yield db
    app.dependency_overrides[get_db] = override_db
    # Admin sign-in needs the authenticator step; stand in for the signed-in user directly.
    app.dependency_overrides[get_current_user] = lambda: CURRENT[-1]
    limiter.reset()
    with TestClient(app) as http:
        yield http
    app.dependency_overrides.clear()
    CURRENT.clear()


def auth(user):
    CURRENT.append(user)
    return {}


@pytest.fixture()
def world(db, make_user):
    admin = make_user(role="admin", email=f"admin-{uuid.uuid4().hex[:6]}@example.com")
    customer, tailor, rider = make_user(role="customer"), make_user(role="tailor"), make_user(role="delivery_partner")
    _, vendor, product, _, _ = catalog(db)
    db.add(DeliveryPartner(user_id=rider.id, vehicle_type="bike", is_verified=True, is_available=True))
    order = Order(order_number="CO-" + uuid.uuid4().hex[:8], order_type="customer_order", buyer_user_id=customer.id,
                  seller_user_id=tailor.id, status="paid", subtotal=Decimal("50000"), total_amount=Decimal("50000"),
                  currency="NGN", ordered_at=utcnow())
    db.add(order); db.flush()
    db.add(Payment(order_id=order.id, provider="interswitch", provider_reference="FH-FAS-" + uuid.uuid4().hex,
                   amount=Decimal("50000"), currency="NGN", status="successful", paid_at=utcnow()))
    db.add(Invoice(invoice_number="INV-" + uuid.uuid4().hex[:8], order_id=order.id, issued_to_user_id=customer.id,
                   issued_by_user_id=tailor.id, line_items_snapshot=[], subtotal=Decimal("50000"), delivery_fee=0,
                   tax_amount=0, discount_amount=0, total_amount=Decimal("50000"), currency="NGN", payment_status="paid",
                   order_date=utcnow()))
    review = Review(order_id=order.id, reviewer_user_id=customer.id, reviewee_user_id=tailor.id, comment="Sleeves too short")
    db.add(review); db.flush()
    db.add(Rating(review_id=review.id, axis="overall", score=2))
    db.commit()
    return admin, customer, tailor, vendor, product


@pytest.mark.parametrize("path", ["vendors", "delivery-partners", "payments", "invoices", "reviews", "reports"])
def test_only_admins_see_the_lists(client, world, path):
    _, customer, *_ = world
    assert client.get(f"/api/v1/admin/{path}", headers=auth(customer)).status_code == 403


def test_admin_lists_show_real_records(client, world):
    admin, customer, tailor, vendor, _ = world
    h = auth(admin)
    vendors = client.get("/api/v1/admin/vendors", headers=h).json()
    assert vendors["total"] >= 1 and vendors["items"][0]["business_name"] == "Verified fabrics"
    assert vendors["items"][0]["active_products"] == 1
    riders = client.get("/api/v1/admin/delivery-partners?online=true", headers=h).json()
    assert riders["total"] == 1 and riders["items"][0]["vehicle_type"] == "bike"
    pay = client.get("/api/v1/admin/payments?status=successful", headers=h).json()
    assert pay["total"] == 1 and pay["items"][0]["amount"] == 50000.0 and pay["items"][0]["buyer_name"] == customer.full_name
    inv = client.get("/api/v1/admin/invoices", headers=h).json()
    assert inv["items"][0]["issued_by"] == tailor.full_name and inv["items"][0]["payment_status"] == "paid"
    low = client.get("/api/v1/admin/reviews?max_score=2", headers=h).json()
    assert low["total"] == 1 and low["items"][0]["score"] == 2.0 and "Sleeves" in low["items"][0]["comment"]
    assert client.get("/api/v1/admin/reviews?max_score=1", headers=h).json()["total"] == 0


def test_reports_count_orders_and_gmv(client, world):
    admin, *_ = world
    r = client.get("/api/v1/admin/reports?days=30", headers=auth(admin)).json()
    assert r["garment_orders"]["placed"] == 1 and r["garment_orders"]["paid"] == 1
    assert r["gmv"] == 50000.0 and r["orders_per_day"][0]["orders"] == 1
    assert set(r["identity_checks"]) == {"submitted", "verified", "rejected", "waiting"}


def test_favorites_list_shows_names_and_photos(client, db, world, make_user):
    _, customer, tailor, _, product = world
    pro = Professional(user_id=tailor.id, professional_type="tailor", business_name="Adire Studio", is_verified=True,
                       shop_photo_url="https://example.com/shop.jpg")
    db.add(pro); db.flush()
    db.add_all([Favorite(user_id=customer.id, favorite_type="professional", favorite_ref_id=pro.id),
                Favorite(user_id=customer.id, favorite_type="vendor_product", favorite_ref_id=product.id)])
    db.commit()
    items = client.get("/api/v1/favorites", headers=auth(customer)).json()
    by_type = {i["favorite_type"]: i for i in items}
    assert by_type["professional"]["title"] == "Adire Studio" and by_type["professional"]["available"] is True
    assert by_type["professional"]["professional_id"] == str(pro.id)
    assert by_type["vendor_product"]["title"] == product.name and by_type["vendor_product"]["subtitle"] == "Verified fabrics"
    pro.is_verified = False
    db.commit()
    again = {i["favorite_type"]: i for i in client.get("/api/v1/favorites", headers=auth(customer)).json()}
    assert again["professional"]["available"] is False
    # An item that's no longer listed can still be removed (but not added again).
    removed = client.post("/api/v1/favorites", json={"favorite_type": "professional", "favorite_ref_id": str(pro.id)}, headers=auth(customer))
    assert removed.status_code == 200 and removed.json() == {"favorited": False}
    readd = client.post("/api/v1/favorites", json={"favorite_type": "professional", "favorite_ref_id": str(pro.id)}, headers=auth(customer))
    assert readd.status_code == 404
