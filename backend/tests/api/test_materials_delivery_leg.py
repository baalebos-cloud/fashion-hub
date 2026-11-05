"""Journey B: materials vendor -> rider -> tailor, as its own traceable delivery leg."""
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.timezone import utcnow
from app.main import app
from app.models.address import Address
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.location import Location
from app.models.order import Order
from app.models.order_timeline import OrderTimelineEntry
from app.models.professional import Professional
from app.models.vendor import Vendor


@pytest.fixture()
def materials(db, make_user):
    vendor_user = make_user(role="vendor", full_name="Lace World")
    tailor = make_user(role="tailor", full_name="Kemi Adeyemi")
    customer = make_user(role="customer")
    rider = make_user(role="delivery_partner", full_name="Sola Bello")
    other_rider = make_user(role="delivery_partner")
    db.add(Vendor(user_id=vendor_user.id, business_name="Lace World", is_verified=True))
    db.add(Professional(user_id=tailor.id, professional_type="tailor", business_name="Kemi Couture", is_verified=True))
    db.add_all([DeliveryPartner(user_id=rider.id, is_verified=True, is_available=True, vehicle_type="bike"),
                DeliveryPartner(user_id=other_rider.id, is_verified=True, is_available=True, vehicle_type="bike")])
    shop = Location(location_type="tailor_shop", formatted_address="14 Iworoko Rd, Ado-Ekiti",
                    city="Ado-Ekiti", state_region="Ekiti", latitude=7.64, longitude=5.22)
    db.add(shop)
    db.flush()
    address = Address(user_id=tailor.id, location_id=shop.id, label="Workshop",
                      recipient_name="Kemi", recipient_phone="+2348011112222")
    db.add(address)
    db.flush()
    garment = Order(order_number="CO-" + uuid.uuid4().hex[:18], order_type="customer_order",
                    buyer_user_id=customer.id, seller_user_id=tailor.id, status="in_production",
                    subtotal=Decimal(50000), total_amount=Decimal(50000), currency="NGN", ordered_at=utcnow())
    db.add(garment)
    db.flush()
    material = Order(order_number="VO-" + uuid.uuid4().hex[:18], order_type="vendor_order",
                     buyer_user_id=tailor.id, seller_user_id=vendor_user.id, status="paid",
                     subtotal=Decimal(12000), total_amount=Decimal(12000), currency="NGN", ordered_at=utcnow(),
                     delivery_address_id=address.id,
                     delivery_address_snapshot={"recipient_name": "Kemi", "recipient_phone": "+2348011112222",
                                                "formatted_address": "14 Iworoko Rd, Ado-Ekiti", "city": "Ado-Ekiti",
                                                "state_region": "Ekiti", "latitude": 7.64, "longitude": 5.22},
                     parent_customer_order_id=garment.id)
    db.add(material)
    db.commit()
    current = [vendor_user]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield {"http": http, "current": current, "db": db, "vendor": vendor_user, "tailor": tailor,
               "customer": customer, "rider": rider, "other_rider": other_rider,
               "material": material, "garment": garment}
    app.dependency_overrides.clear()


def _advance_to_ready(http, order_id):
    for status in ("confirmed", "processing", "ready_for_pickup"):
        response = http.post(f"/api/v1/orders/{order_id}/vendor-fulfillment", json={"target_status": status})
        assert response.status_code == 200, response.text


def test_materials_leg_from_vendor_to_tailor(materials):
    http, current, db = materials["http"], materials["current"], materials["db"]
    material, garment = materials["material"], materials["garment"]
    _advance_to_ready(http, material.id)

    # The vendor must set a pickup point before requesting a rider.
    blocked = http.post(f"/api/v1/delivery-requests/orders/{material.id}")
    assert blocked.status_code == 409 and "pickup location" in blocked.text
    saved = http.patch("/api/v1/vendors/me/location", params={
        "latitude": 7.62, "longitude": 5.23, "formatted_address": "3 Fajuyi Market, Ado-Ekiti",
        "city": "Ado-Ekiti", "state_region": "Ekiti"})
    assert saved.status_code == 200 and saved.json()["warehouse_location_id"]
    from sqlalchemy import text
    geom = db.execute(text("SELECT ST_AsText(geom) FROM locations WHERE id = :id"),
                      {"id": saved.json()["warehouse_location_id"]}).scalar()
    assert geom == "POINT(5.23 7.62)"  # vendor stays discoverable in nearby-vendor search
    requested = http.post(f"/api/v1/delivery-requests/orders/{material.id}")
    assert requested.status_code == 201, requested.text
    request_id = requested.json()["id"]

    # Riders see a priced job card with areas only, and the vendor sees it in their dispatch panel.
    current[0] = materials["rider"]
    jobs = http.get("/api/v1/delivery-requests/available").json()
    job = next(j for j in jobs if j["id"] == request_id)
    assert job["pickup_area"] == "Ado-Ekiti, Ekiti" and job["suggested_fare"] >= 1000
    assert "Fajuyi" not in str(jobs) and "Iworoko" not in str(jobs)
    current[0] = materials["vendor"]
    assert http.get(f"/api/v1/delivery-requests/orders/{material.id}/dispatch").json()["request"]["status"] == "requested"

    # Rider claims, collects and travels; only one rider can win the job.
    current[0] = materials["rider"]
    delivery_id = http.post(f"/api/v1/delivery-requests/{request_id}/accept").json()["id"]
    current[0] = materials["other_rider"]
    assert http.post(f"/api/v1/delivery-requests/{request_id}/accept").status_code in {404, 409}
    current[0] = materials["rider"]
    assert http.post(f"/api/v1/deliveries/{delivery_id}/delivered", json={"handover_code": "000000"}).status_code == 409
    assert http.post(f"/api/v1/deliveries/{delivery_id}/picked-up").status_code == 200
    db.refresh(material)
    assert material.status == "in_transit"
    assert [e.to_status for e in db.query(OrderTimelineEntry).filter_by(order_id=material.id)
            .order_by(OrderTimelineEntry.created_at)][-2:] == ["picked_up", "in_transit"]

    # The tailor (buyer) holds the handover code; a wrong code never completes delivery.
    assert http.get(f"/api/v1/deliveries/{delivery_id}/handover-code").status_code == 404
    current[0] = materials["tailor"]
    code = http.get(f"/api/v1/deliveries/{delivery_id}/handover-code").json()["handover_code"]
    current[0] = materials["rider"]
    wrong = "000000" if code != "000000" else "111111"
    assert http.post(f"/api/v1/deliveries/{delivery_id}/delivered", json={"handover_code": wrong}).status_code >= 400
    assert db.get(Delivery, uuid.UUID(delivery_id)).status == "in_transit"
    assert http.post(f"/api/v1/deliveries/{delivery_id}/delivered", json={"handover_code": code}).status_code == 200
    db.refresh(material)
    assert material.status == "delivered"

    # Tailor confirms receipt; the linked customer garment order is untouched.
    current[0] = materials["customer"]
    assert http.post(f"/api/v1/orders/{material.id}/materials-received", json={}).status_code == 403
    current[0] = materials["tailor"]
    received = http.post(f"/api/v1/orders/{material.id}/materials-received", json={"note": "All 6 yards received"})
    assert received.status_code == 200 and received.json()["status"] == "completed"
    assert http.post(f"/api/v1/orders/{material.id}/materials-received", json={}).json()["status"] == "completed"
    db.refresh(garment)
    assert garment.status == "in_production"

    journey = http.get(f"/api/v1/deliveries/orders/{material.id}/journey").json()
    states = {m["key"]: m["state"] for m in journey["milestones"]}
    assert states["delivered"] == "done" and states["received"] == "done"
    assert "in_production" not in states  # materials journey skips garment-only steps


def test_only_the_vendor_can_dispatch_and_only_when_ready(materials):
    http, current, material = materials["http"], materials["current"], materials["material"]
    http.patch("/api/v1/vendors/me/location", params={"latitude": 7.62, "longitude": 5.23})
    assert http.post(f"/api/v1/delivery-requests/orders/{material.id}").status_code == 409  # still "paid"
    _advance_to_ready(http, material.id)
    current[0] = materials["tailor"]  # the buyer cannot dispatch the seller's leg
    assert http.post(f"/api/v1/delivery-requests/orders/{material.id}").status_code == 403
    current[0] = materials["customer"]
    assert http.patch("/api/v1/vendors/me/location", params={"latitude": 1, "longitude": 1}).status_code == 403


def test_receipt_cannot_be_confirmed_before_delivery(materials):
    http, current, material = materials["http"], materials["current"], materials["material"]
    current[0] = materials["tailor"]
    response = http.post(f"/api/v1/orders/{material.id}/materials-received", json={})
    assert response.status_code == 409


def test_customer_order_dispatch_is_unchanged(materials):
    """Regression: a tailor still cannot request a rider for an order that isn't ready."""
    http, current, garment = materials["http"], materials["current"], materials["garment"]
    current[0] = materials["tailor"]
    assert http.post(f"/api/v1/delivery-requests/orders/{garment.id}").status_code == 409
