"""Phase 7: Nigerian address details, rider-approaching/arrived alerts, and the materials leg
shown on the customer order."""
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.core.timezone import utcnow
from app.main import app
from app.models.address import Address
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_proof import DeliveryEvent
from app.models.delivery_request import DeliveryRequest
from app.models.location import Location
from app.models.notification import Notification
from app.models.order import Order
from app.models.professional import Professional
from app.models.vendor import Vendor
from app.services.order_service import OrderService
from tests.catalog_helpers import catalog_request

DROP = (6.4500000, 3.4700000)  # Lekki
LOCAL = {"lga": "Eti-Osa", "landmark": "Opposite the blue mosque",
         "nearest_bus_stop": "Jakande bus stop", "delivery_instructions": "Call at the gate"}


@pytest.fixture()
def client(db):
    limiter.reset()
    current = [None]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield http, current
    app.dependency_overrides.clear()


def test_saved_address_keeps_nigerian_details_and_blanks_become_empty(db, make_user, client):
    http, current = client
    current[0] = make_user()
    created = http.post("/api/v1/addresses", json={
        "label": "Home", "recipient_name": "Ada Obi", "recipient_phone": "08031234567",
        "formatted_address": "14 Admiralty Way, Lekki", "city": "Lekki", "state_region": "Lagos",
        "latitude": DROP[0], "longitude": DROP[1], **LOCAL, "landmark": ""})
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["lga"] == "Eti-Osa" and body["nearest_bus_stop"] == "Jakande bus stop"
    assert body["landmark"] is None
    assert http.get("/api/v1/addresses").json()[0]["delivery_instructions"] == "Call at the gate"


def test_address_details_reach_the_assigned_rider_and_stay_frozen(db, make_user, client):
    http, current = client
    buyer, seller, rider = make_user(), make_user(role="tailor"), make_user(role="delivery_partner")
    request = catalog_request(db, buyer, seller)
    home = db.get(Location, db.get(Address, request["delivery_address_id"]).location_id)
    for field, value in LOCAL.items():
        setattr(home, field, value)
    home.latitude, home.longitude = DROP
    order = OrderService(db).create_customer_order(**request)
    assert order.delivery_address_snapshot["lga"] == "Eti-Osa"
    shop = Location(location_type="tailor_shop", formatted_address="Yaba workshop", city="Lagos",
                    latitude=6.51, longitude=3.37, landmark="Beside Tejuosho market")
    db.add(shop)
    db.flush()
    db.query(Professional).filter_by(user_id=seller.id).one().location_id = shop.id
    order.status = "ready_for_delivery"
    db.add(DeliveryPartner(user_id=rider.id, is_verified=True, is_available=True, vehicle_type="bike"))
    db.commit()

    current[0] = seller
    job = http.post(f"/api/v1/delivery-requests/orders/{order.id}").json()
    # The customer edits their saved address later: the dispatched route must not move.
    home.landmark = "Changed landmark"
    db.commit()
    current[0] = rider
    delivery_id = http.post(f"/api/v1/delivery-requests/{job['id']}/accept").json()["id"]
    trip = http.get(f"/api/v1/deliveries/{delivery_id}/trip").json()
    assert {k: trip["dropoff"][k] for k in LOCAL} == LOCAL
    assert trip["pickup"]["landmark"] == "Beside Tejuosho market"


@pytest.fixture()
def moving(db, make_user, client, monkeypatch):
    monkeypatch.setattr(settings, "DELIVERY_PROXIMITY_ALERTS_ENABLED", True)
    http, current = client
    buyer, seller, rider = make_user(), make_user(role="tailor"), make_user(role="delivery_partner")
    partner = DeliveryPartner(user_id=rider.id, is_verified=True, is_available=False, vehicle_type="bike")
    pickup = Location(location_type="delivery_pickup", latitude=6.51, longitude=3.37)
    dropoff = Location(location_type="delivery_dropoff", latitude=DROP[0], longitude=DROP[1])
    order = Order(order_number="P7-" + uuid.uuid4().hex[:10].upper(), order_type="customer_order",
                  buyer_user_id=buyer.id, seller_user_id=seller.id, status="out_for_delivery",
                  subtotal=40000, total_amount=40000, currency="NGN", ordered_at=utcnow())
    db.add_all([partner, pickup, dropoff, order])
    db.flush()
    req = DeliveryRequest(order_id=order.id, pickup_location_id=pickup.id, dropoff_location_id=dropoff.id,
                          status="assigned")
    db.add(req)
    db.flush()
    delivery = Delivery(order_id=order.id, delivery_request_id=req.id, status="in_transit", provider="internal",
                        delivery_fee=2000, delivery_partner_id=partner.id)
    db.add(delivery)
    db.commit()
    current[0] = rider
    base = f"/api/v1/deliveries/{delivery.id}/position"
    token = http.post(base + "/start").json()["share_token"]

    clock = [utcnow() - timedelta(seconds=100)]

    def ping(lat, lng, accuracy=15):
        # Real phones send a fix every few seconds; the server ignores points < 3 s apart.
        clock[0] += timedelta(seconds=5)
        current[0] = rider
        response = http.post(base, json={"latitude": lat, "longitude": lng, "accuracy_m": accuracy,
                                         "share_token": token, "recorded_at": clock[0].isoformat()})
        assert response.status_code == 200, response.text

    def alerts():
        # Which alerts were sent, in a fixed order. Notifications made in one test transaction can
        # share a created_at, so their order isn't meaningful here; the order alerts happened in is
        # checked through DeliveryEvent.seq instead.
        return sorted(n.event_type for n in db.query(Notification).filter_by(recipient_user_id=buyer.id).all()
                      if n.event_type.startswith("delivery.rider_"))
    return {"ping": ping, "alerts": alerts, "delivery": delivery, "db": db, "buyer": buyer}


def test_buyer_is_told_once_when_the_rider_is_close_and_once_on_arrival(moving):
    ping, alerts, db = moving["ping"], moving["alerts"], moving["db"]
    ping(6.50, 3.40)                      # ~6.5 km out: nothing yet
    assert alerts() == []
    ping(6.459, 3.47)                     # ~1 km: about 4 min away on a bike
    ping(6.458, 3.47)                     # still close: no repeat
    assert alerts() == ["delivery.rider_approaching"]
    note = db.query(Notification).filter_by(event_type="delivery.rider_approaching").one()
    assert "min away" in note.title and "6.45" not in note.body and "3.47" not in note.body
    ping(DROP[0], DROP[1], accuracy=180)  # at the door but GPS too vague: not "arrived"
    assert alerts() == ["delivery.rider_approaching"]
    ping(DROP[0] + 0.0005, DROP[1])       # ~55 m, good fix
    ping(DROP[0], DROP[1])
    assert alerts() == ["delivery.rider_approaching", "delivery.rider_arrived"]
    events = [e.event_type for e in db.query(DeliveryEvent).filter_by(delivery_id=moving["delivery"].id)
              .order_by(DeliveryEvent.seq)]
    assert events == ["rider_approaching", "rider_arrived"]


def test_arriving_without_an_earlier_fix_only_sends_arrived(moving):
    moving["ping"](DROP[0], DROP[1])
    moving["ping"](6.459, 3.47)
    assert moving["alerts"]() == ["delivery.rider_arrived"]


def test_alerts_can_be_switched_off(moving, monkeypatch):
    monkeypatch.setattr(settings, "DELIVERY_PROXIMITY_ALERTS_ENABLED", False)
    moving["ping"](DROP[0], DROP[1])
    assert moving["alerts"]() == []


def test_customer_order_shows_the_materials_leg_without_vendor_details(db, make_user, client):
    http, current = client
    buyer, tailor, vendor_user, rider = (make_user(), make_user(role="tailor"), make_user(role="vendor"),
                                         make_user(role="delivery_partner"))
    db.add(Vendor(user_id=vendor_user.id, business_name="Balogun Fabrics", is_verified=True))
    garment = Order(order_number="CO-" + uuid.uuid4().hex[:10].upper(), order_type="customer_order",
                    buyer_user_id=buyer.id, seller_user_id=tailor.id, status="in_production",
                    subtotal=90000, total_amount=90000, currency="NGN", ordered_at=utcnow())
    db.add(garment)
    db.flush()

    def material(status, amount):
        return Order(order_number="VO-" + uuid.uuid4().hex[:10].upper(), order_type="vendor_order",
                     buyer_user_id=tailor.id, seller_user_id=vendor_user.id, status=status,
                     subtotal=amount, total_amount=amount, currency="NGN", ordered_at=utcnow(),
                     parent_customer_order_id=garment.id,
                     delivery_address_snapshot={"formatted_address": "Tailor's secret workshop"})
    shipped = material("in_transit", 27350)
    shipped.paid_at = utcnow()
    abandoned = material("cancelled", 22220)  # linked, never paid, then cancelled
    db.add_all([shipped, material("checkout", 11110), abandoned])
    partner = DeliveryPartner(user_id=rider.id, is_verified=True)
    db.add(partner)
    db.flush()
    db.add(Delivery(order_id=garment.id, delivery_request_id=uuid.uuid4(), status="assigned", provider="internal",
                    delivery_fee=1500, delivery_partner_id=partner.id))
    db.commit()

    url = f"/api/v1/deliveries/orders/{garment.id}/journey"
    for who in (buyer, tailor):
        current[0] = who
        response = http.get(url)
        assert response.status_code == 200, response.text
        legs = response.json()["materials_legs"]
        assert [(leg["vendor_name"], leg["label"], leg["done"]) for leg in legs] == [
            ("Balogun Fabrics", "Materials on their way to your tailor", False)]
        for private in ("27350", "11110", "22220", "secret workshop"):
            assert private not in response.text
    current[0] = rider
    assert http.get(url).json()["materials_legs"] == []
