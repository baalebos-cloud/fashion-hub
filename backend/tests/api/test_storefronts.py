"""Shareable storefront links: one namespace, verified-only public pages, no private data."""
import uuid

from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.design import Design
from app.models.location import Location
from app.models.order import Order
from app.models.professional import Professional
from app.models.vendor import Vendor
from app.models.vendor_product import VendorProduct
from app.services.storefront_handles import candidate_handles, is_valid_handle


def _client(db, current):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    return TestClient(app)


def test_handle_rules():
    assert is_valid_handle("kemi-couture")
    for bad in ("ab", "-kemi", "kemi-", "kemi--couture", "Kemi", "kemi_couture", "tailora", "support"):
        assert not is_valid_handle(bad), bad
    assert next(candidate_handles("Àdùnní Stitches!", "x")) == "adunni-stitches"
    assert next(candidate_handles("Tailora", "1234-5678-9abc")) == "tailora-2"
    assert next(candidate_handles("", "1234-5678-9abc")) == "shop-123456789a"


def test_owner_gets_link_and_page_goes_live_only_after_verification(db, make_user):
    tailor = make_user(role="tailor", full_name="Kemi Adeyemi", phone_number="+2348011111111")
    location = Location(location_type="business", city="Ikeja", state_region="Lagos",
                        formatted_address="12 Secret Close, Ikeja", latitude=6.6, longitude=3.35)
    db.add(location)
    db.flush()
    profile = Professional(user_id=tailor.id, professional_type="tailor", business_name="Kemi Couture",
                           bio="Bespoke agbada.", is_verified=False, location_id=location.id)
    db.add(profile)
    db.flush()
    db.add(Design(professional_id=profile.id, title="Wedding agbada", base_price=85000, currency="NGN"))
    db.commit()
    current = [tailor]
    try:
        with _client(db, current) as http:
            link = http.get("/api/v1/storefronts/me").json()
            assert link["handle"] == "kemi-couture"
            assert link["share_url"].endswith("/s/kemi-couture")
            assert link["is_public"] is False
            assert http.get("/api/v1/storefronts/kemi-couture").status_code == 404

            profile.is_verified = True
            db.commit()
            page = http.get("/api/v1/storefronts/KEMI-COUTURE")
            assert page.status_code == 200, page.text
            body = page.json()
            assert body["kind"] == "tailor" and body["is_verified"] is True
            assert body["area"] == "Ikeja, Lagos"
            assert [d["title"] for d in body["designs"]] == ["Wedding agbada"]
            raw = page.text
            for private in ("Secret Close", tailor.email, "+2348011111111", "Adeyemi", "6.6"):
                assert private not in raw
    finally:
        app.dependency_overrides.clear()


def test_handles_are_unique_across_professionals_and_vendors(db, make_user):
    tailor, vendor_user = make_user(role="tailor"), make_user(role="vendor")
    db.add(Professional(user_id=tailor.id, professional_type="tailor", business_name="Ankara House",
                        is_verified=True))
    db.add(Vendor(user_id=vendor_user.id, business_name="Fabric Hub", is_verified=True))
    db.commit()
    current = [tailor]
    try:
        with _client(db, current) as http:
            assert http.get("/api/v1/storefronts/me").json()["handle"] == "ankara-house"
            current[0] = vendor_user
            assert http.put("/api/v1/storefronts/me", json={"handle": "ankara-house"}).status_code == 409
            assert http.put("/api/v1/storefronts/me", json={"handle": "tailora"}).status_code == 422
            changed = http.put("/api/v1/storefronts/me", json={"handle": "fabric-hub-lagos"})
            assert changed.status_code == 200, changed.text
            assert changed.json()["is_public"] is True
    finally:
        app.dependency_overrides.clear()


def test_vendor_storefront_lists_only_active_products(db, make_user):
    vendor_user = make_user(role="vendor")
    vendor = Vendor(user_id=vendor_user.id, business_name="Lace World", is_verified=True)
    db.add(vendor)
    db.flush()
    db.add_all([
        VendorProduct(vendor_id=vendor.id, name="Swiss lace", base_price=12000, is_active=True),
        VendorProduct(vendor_id=vendor.id, name="Retired lace", base_price=9000, is_active=False),
    ])
    db.commit()
    current = [vendor_user]
    try:
        with _client(db, current) as http:
            handle = http.get("/api/v1/storefronts/me").json()["handle"]
            body = http.get(f"/api/v1/storefronts/{handle}").json()
            assert body["kind"] == "vendor"
            assert [p["name"] for p in body["products"]] == ["Swiss lace"]
    finally:
        app.dependency_overrides.clear()


def test_customers_cannot_claim_a_storefront(db, make_user):
    current = [make_user(role="customer")]
    try:
        with _client(db, current) as http:
            assert http.get("/api/v1/storefronts/me").status_code == 403
            assert http.get("/api/v1/storefronts/no-such-shop").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_order_tracking_shows_rider_card(db, make_user):
    buyer, seller = make_user(), make_user(role="tailor")
    rider = make_user(role="delivery_partner", full_name="Sola Rider")
    partner = DeliveryPartner(user_id=rider.id, vehicle_type="bike", is_verified=True)
    db.add(partner)
    order = Order(order_number="SF-" + uuid.uuid4().hex[:20], order_type="customer_order",
                  buyer_user_id=buyer.id, seller_user_id=seller.id, status="shipped",
                  subtotal=100, total_amount=100, currency="NGN")
    db.add(order)
    db.flush()
    db.add(Delivery(order_id=order.id, delivery_request_id=uuid.uuid4(), status="in_transit",
                    provider="internal", delivery_fee=0, delivery_partner_id=partner.id))
    db.commit()
    current = [buyer]
    try:
        with _client(db, current) as http:
            card = http.get(f"/api/v1/deliveries/orders/{order.id}/tracking").json()
            assert card["rider_verified"] is True
            assert card["rider_vehicle_type"] == "bike"
            assert card["rider_completed_deliveries"] == 0
    finally:
        app.dependency_overrides.clear()
