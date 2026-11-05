"""Full internal dispatch regression: buyer data stays private and only the
assigned courier can update paid customer-order fulfillment."""
import uuid
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.address import Address
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
    admin = make_user(role="admin")
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
            # Dispatch owns immutable coordinates, not mutable shop/address pointers.
            from app.models.delivery_request import DeliveryRequest
            saved_request = db.get(DeliveryRequest, uuid.UUID(requested["id"]))
            assert str(saved_request.pickup_location_id) != str(shop.id)
            assert db.get(Location, saved_request.pickup_location_id).formatted_address == "Test tailoring shop"
            shop.formatted_address = "Moved workshop location"
            db.commit()
            assert db.get(Location, saved_request.pickup_location_id).formatted_address == "Test tailoring shop"
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
            assert client.get("/api/v1/admin/dispatch-board").status_code == 403
            current[0] = admin
            board = client.get("/api/v1/admin/dispatch-board")
            assert board.status_code == 200, board.text
            assert board.json()["unassigned_count"] == 1
            current[0] = courier

            accepted = client.post(f"/api/v1/delivery-requests/{requested['id']}/accept")
            assert accepted.status_code == 200, accepted.text
            delivery_id = accepted.json()["id"]
            assert accepted.json()["status"] == "assigned"
            current[0] = admin
            board = client.get("/api/v1/admin/dispatch-board")
            assert board.status_code == 200
            assert board.json()["active_count"] == 1
            current[0] = courier
            trip = client.get(f"/api/v1/deliveries/{delivery_id}/trip")
            assert trip.status_code == 200, trip.text
            assert trip.json()["pickup"]["address"] == "Test tailoring shop"
            assert trip.json()["distance_source"] == "haversine"
            # The customer's later deletion of their saved address cannot
            # erase recipient details or change an already assigned route.
            saved_address = db.get(Address, order.delivery_address_id)
            db.delete(saved_address)
            db.commit()
            trip = client.get(f"/api/v1/deliveries/{delivery_id}/trip")
            assert trip.status_code == 200
            assert trip.json()["dropoff"]["contact_name"] == "Test Customer"
            # The snapshot still lets the rider reach the recipient, but only via
            # a masked call: the real number never leaves the server.
            assert trip.json()["dropoff"]["can_call"] is True
            assert "+2348012345678" not in trip.text and "contact_phone" not in trip.text
            assert client.post(f"/api/v1/delivery-requests/{requested['id']}/accept").status_code in {403, 404}

            pickup = f"/api/v1/deliveries/{delivery_id}/picked-up"
            dropoff = f"/api/v1/deliveries/{delivery_id}/delivered"
            # A ready order can be picked up immediately after assignment:
            # no artificial seller-side "shipped" state change is required.
            current[0] = other_courier
            assert client.post(pickup).status_code == 404
            assert client.get(f"/api/v1/deliveries/{delivery_id}").status_code == 404
            current[0] = courier
            assert client.post(pickup).status_code == 422  # seller's pickup code required
            current[0] = seller
            pickup_code = client.get(f"/api/v1/deliveries/{delivery_id}/pickup-code").json()["pickup_code"]
            current[0] = courier
            response = client.post(pickup, json={"pickup_code": pickup_code})
            assert response.status_code == 200, response.text
            assert response.json()["status"] == "in_transit"
            db.refresh(order)
            assert order.status == "out_for_delivery"
            assert order.shipped_at is not None
            assert client.post(pickup, json={"pickup_code": pickup_code}).status_code == 409
            # Rider-initiated location sharing; unassigned accounts cannot read or publish.
            gps = f"/api/v1/deliveries/{delivery_id}/position"
            share = client.post(gps + "/start")
            assert share.status_code == 200, share.text
            token = share.json()["share_token"]
            assert len(token) >= 32
            update = {"latitude": 7.64037, "longitude": 5.22102,
                      "accuracy_m": 12, "share_token": token}
            assert client.post(gps, json=update).status_code == 200
            current[0] = other_courier
            assert client.get(gps).status_code == 404
            assert client.post(gps, json=update).status_code == 404
            current[0] = buyer
            shared = client.get(gps)
            assert shared.status_code == 200 and shared.json()["latitude"] == 7.64037
            assert "share_token" not in shared.json()
            current[0] = courier
            assert client.delete(gps).status_code == 204
            assert client.post(gps, json=update).status_code == 403
            current[0] = buyer
            assert client.get(gps).json() is None
            # Only the buyer may view the code, and the rider must provide it.
            current[0] = buyer
            code_response = client.get(f"/api/v1/deliveries/{delivery_id}/handover-code")
            assert code_response.status_code == 200, code_response.text
            code = code_response.json()["handover_code"]
            assert len(code) == 6
            current[0] = other_courier
            assert client.get(f"/api/v1/deliveries/{delivery_id}/handover-code").status_code == 404
            current[0] = courier
            assert client.post(dropoff, json={}).status_code == 422
            assert client.post(dropoff, json={"handover_code": "999999" if code != "999999" else "888888"}).status_code == 422
            response = client.post(dropoff, json={"handover_code": code})
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
