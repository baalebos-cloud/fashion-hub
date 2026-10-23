"""GPS writes require assigned, verified couriers and valid coordinates."""
import uuid

from fastapi.testclient import TestClient
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.order import Order


def test_courier_ping_ownership_and_coordinate_validation(db, make_user):
    customer, seller = make_user(), make_user(role="tailor")
    courier, intruder = make_user(role="delivery_partner"), make_user(role="delivery_partner")
    order = Order(order_number="GP-" + uuid.uuid4().hex[:20], order_type="customer_order",
                  buyer_user_id=customer.id, seller_user_id=seller.id,
                  status="out_for_delivery", subtotal=100, total_amount=100, currency="NGN")
    partner = DeliveryPartner(user_id=courier.id, is_verified=True, is_available=True)
    db.add_all([order, partner])
    db.flush()
    delivery = Delivery(order_id=order.id, delivery_request_id=uuid.uuid4(),
                        delivery_partner_id=partner.id, status="in_transit",
                        provider="internal", delivery_fee=0)
    db.add(delivery)
    db.commit()
    current = [intruder]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    try:
        with TestClient(app) as client:
            endpoint = f"/api/v1/delivery-tracking/{delivery.id}/pings"
            payload = {"latitude": 6.5, "longitude": 3.4, "eta_minutes": 20}
            assert client.post(endpoint, json=payload).status_code == 404
            current[0] = courier
            assert client.post(endpoint, json={**payload, "latitude": 100}).status_code == 422
            response = client.post(endpoint, json=payload)
            assert response.status_code == 200, response.text
            assert response.json()["current_latitude"] == 6.5
            assert response.json()["current_status"] == "in_transit"
            delivery.status = "delivered"
            db.commit()
            assert client.post(endpoint, json=payload).status_code == 404
    finally:
        app.dependency_overrides.clear()
