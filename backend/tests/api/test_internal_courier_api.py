"""Full internal dispatch regression: buyer data stays private and only the
assigned courier can update paid customer-order fulfillment."""
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.location import Location
from app.models.order_timeline import OrderTimelineEntry
from app.models.professional import Professional
from app.services.order_service import OrderService
from tests.catalog_helpers import catalog_request


def test_internal_dispatch_assigned_delivery_and_customer_visibility(db, make_user):
    buyer = make_user()
    seller = make_user(role="tailor")
    courier = make_user(role="delivery_partner")
    other_courier = make_user(role="delivery_partner")
    order = OrderService(db).create_customer_order(
        **catalog_request(db, buyer, seller)
    )
    shop = Location(location_type="tailor_shop", formatted_address="Test tailoring shop", city="Lagos")
    db.add(shop)
    db.flush()
    db.query(Professional).filter_by(user_id=seller.id).one().location_id = shop.id
    order.status = "ready_for_delivery"
    db.commit()

    rider_profile = DeliveryPartner(user_id=courier.id, is_verified=True, is_available=True)
    db.add(rider_profile)
    db.commit()

    current = [seller]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    try:
        with TestClient(app) as client:
            route = f"/api/v1/delivery-requests/orders/{order.id}"
            response = client.post(route)
            assert response.status_code == 201, response.text
            requested = response.json()
            assert requested["status"] == "requested"
            assert client.post(route).json()["id"] == requested["id"]

            current[0] = buyer
            assert client.post(route).status_code == 403
            current[0] = other_courier
            assert client.get("/api/v1/delivery-requests/available").status_code == 403
            current[0] = courier
            available = client.get("/api/v1/delivery-requests/available")
            assert available.status_code == 200 and len(available.json()) == 1
            assert "dropoff_location_id" not in available.json()[0]
            assert "pickup_location_id" not in available.json()[0]

            accepted = client.post(f"/api/v1/delivery-requests/{requested['id']}/accept")
            assert accepted.status_code == 200, accepted.text
            delivery_id = accepted.json()["id"]
            assert accepted.json()["status"] == "assigned"
            assert client.post(f"/api/v1/delivery-requests/{requested['id']}/accept").status_code in {403, 404}

            pickup = f"/api/v1/deliveries/{delivery_id}/picked-up"
            dropoff = f"/api/v1/deliveries/{delivery_id}/delivered"
            assert client.post(pickup).status_code == 409
            order.status = "shipped"
            db.commit()
            current[0] = other_courier
            assert client.post(pickup).status_code == 404
            assert client.get(f"/api/v1/deliveries/{delivery_id}").status_code == 404
            current[0] = courier
            response = client.post(pickup)
            assert response.status_code == 200, response.text
            assert response.json()["status"] == "in_transit"
            db.refresh(order)
            assert order.status == "out_for_delivery"
            assert client.post(pickup).status_code == 409
            response = client.post(dropoff)
            assert response.status_code == 200, response.text
            assert response.json()["status"] == "delivered"
            db.refresh(order)
            db.refresh(rider_profile)
            assert order.status == "delivered"
            assert rider_profile.is_available is True
            assert (db.query(OrderTimelineEntry)
                    .filter_by(order_id=order.id, to_status="delivered").count()) == 1
            current[0] = buyer
            assert client.get(f"/api/v1/deliveries/{delivery_id}").status_code == 200
            current[0] = seller
            assert client.get(f"/api/v1/deliveries/{delivery_id}").status_code == 200
    finally:
        app.dependency_overrides.clear()
