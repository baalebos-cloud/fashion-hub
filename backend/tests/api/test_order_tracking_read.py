"""Delivery tracking reads use owned, persisted snapshots and do not leak locations."""
import uuid
from fastapi.testclient import TestClient
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.order import Order
from app.models.delivery import Delivery
from app.models.delivery_tracking import DeliveryTracking
from app.core.timezone import utcnow


def test_tracking_requires_order_ownership_and_reads_real_position(db, make_user):
    buyer, seller, stranger = make_user(), make_user(role="tailor"), make_user()
    order = Order(order_number="TR-" + uuid.uuid4().hex[:20],
                  order_type="customer_order", buyer_user_id=buyer.id, seller_user_id=seller.id,
                  status="shipped", subtotal=100, total_amount=100, currency="NGN")
    db.add(order)
    db.commit()
    current = [buyer]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    try:
        with TestClient(app) as client:
            endpoint = f"/api/v1/orders/{order.id}/tracking"
            assert client.get(endpoint).json()["tracking"] is None
            delivery = Delivery(order_id=order.id, delivery_request_id=uuid.uuid4(),
                                status="in_transit", provider="internal", delivery_fee=0)
            db.add(delivery)
            db.flush()
            db.add(DeliveryTracking(delivery_id=delivery.id, current_status="in_transit",
                                    current_latitude=6.5, current_longitude=3.4,
                                    eta_minutes=20, last_ping_at=utcnow()))
            db.commit()
            body = client.get(endpoint).json()
            assert body["tracking"]["delivery_id"] == str(delivery.id)
            assert body["tracking"]["current_latitude"] == 6.5
            assert body["tracking"]["is_stale"] is False
            assert body["tracking"]["eta_minutes"] == 20
            current[0] = stranger
            assert client.get(endpoint).status_code == 403
            current[0] = seller
            assert client.get(endpoint).status_code == 200
    finally:
        app.dependency_overrides.clear()
