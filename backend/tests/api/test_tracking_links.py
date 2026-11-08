"""Phase 4: shareable recipient tracking links (hashed, scoped, expiring, revocable, narrow)."""
import re
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
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_share_link import DeliveryShareLink
from app.models.order import Order
from app.models.professional import Professional
from app.services.share_link_service import hash_token


@pytest.fixture()
def shared(db, make_user):
    limiter.reset()
    buyer = make_user(full_name="Ada Obi", phone_number="+2348031110001")
    seller = make_user(role="tailor", phone_number="+2348031110002")
    rider = make_user(role="delivery_partner", full_name="Sola Bello", phone_number="+2348031110003")
    stranger = make_user()
    db.add(Professional(user_id=seller.id, professional_type="tailor", business_name="Kemi Couture", is_verified=True))
    partner = DeliveryPartner(user_id=rider.id, vehicle_type="bike", is_verified=True)
    db.add(partner)
    order = Order(order_number="TL-" + uuid.uuid4().hex[:10].upper(), order_type="customer_order",
                  buyer_user_id=buyer.id, seller_user_id=seller.id, status="out_for_delivery",
                  subtotal=85000, total_amount=85000, currency="NGN", ordered_at=utcnow(),
                  delivery_address_snapshot={"recipient_name": "Mama Ada", "recipient_phone": "+2348039999999",
                                             "formatted_address": "14 Secret Close, Lekki", "city": "Lekki",
                                             "state_region": "Lagos", "latitude": 6.44, "longitude": 3.47})
    db.add(order)
    db.flush()
    db.add(Delivery(order_id=order.id, delivery_request_id=uuid.uuid4(), status="in_transit",
                    provider="internal", delivery_fee=3600, delivery_partner_id=partner.id))
    db.commit()
    current = [buyer]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield {"http": http, "current": current, "db": db, "order": order, "buyer": buyer,
               "seller": seller, "stranger": stranger}
    app.dependency_overrides.clear()


def _token(url: str) -> str:
    return url.rsplit("/track/", 1)[1]


def test_buyer_shares_a_link_and_the_recipient_sees_a_narrow_view(shared):
    http, db, order = shared["http"], shared["db"], shared["order"]
    created = http.post(f"/api/v1/orders/{order.id}/share-links", json={"label": "Mum"})
    assert created.status_code == 201, created.text
    url = created.json()["url"]
    token = _token(url)
    assert url.startswith(settings.FRONTEND_URL.rstrip("/") + "/track/") and len(token) >= 43
    stored = db.query(DeliveryShareLink).one()
    assert stored.token_hash == hash_token(token) and token not in str(stored.__dict__)

    shared["current"][0] = None  # public: no login
    app.dependency_overrides.pop(get_current_user)
    view = http.get(f"/api/v1/public/track/{token}")
    assert view.status_code == 200, view.text
    assert view.headers["cache-control"] == "no-store" and "noindex" in view.headers["x-robots-tag"]
    body = view.json()
    assert body["tracking_number"] == order.order_number and body["seller_name"] == "Kemi Couture"
    assert body["dropoff_area"] == "Lekki, Lagos"
    assert body["rider"] == {"first_name": "Sola", "vehicle_type": "bike", "is_verified": True, "rating": 0.0}
    assert any(m["key"] == "picked_up" for m in body["milestones"])
    # Timestamps can contain digit runs like "3.47" by chance; check everything else.
    visible = re.sub(r"\d{4}-\d{2}-\d{2}T[0-9:.]+(?:Z|[+-]\d{2}:\d{2})?", "<time>", view.text)
    for private in ("Secret Close", "Mama Ada", "+234", "6.44", "3.47", "85000", "3600", "handover",
                    "Bello", "Obi", shared["buyer"].email):
        assert private not in visible, private
    assert "latitude" not in visible and "longitude" not in visible
    assert db.query(DeliveryShareLink).one().access_count == 1


def test_only_the_buyer_can_create_list_or_revoke_links(shared):
    http, current, order = shared["http"], shared["current"], shared["order"]
    link_id = http.post(f"/api/v1/orders/{order.id}/share-links", json={}).json()["id"]
    for who in ("seller", "stranger"):
        current[0] = shared[who]
        assert http.post(f"/api/v1/orders/{order.id}/share-links", json={}).status_code == 404
        assert http.get(f"/api/v1/orders/{order.id}/share-links").status_code == 404
        assert http.delete(f"/api/v1/orders/{order.id}/share-links/{link_id}").status_code == 404
    current[0] = shared["buyer"]
    links = http.get(f"/api/v1/orders/{order.id}/share-links").json()
    assert links[0]["active"] is True and "token" not in str(links) and "url" not in links[0]


def test_revoked_expired_and_garbage_tokens_all_look_the_same(shared):
    http, db, order = shared["http"], shared["db"], shared["order"]
    revoked = http.post(f"/api/v1/orders/{order.id}/share-links", json={}).json()
    expired = http.post(f"/api/v1/orders/{order.id}/share-links", json={}).json()
    assert http.delete(f"/api/v1/orders/{order.id}/share-links/{revoked['id']}").status_code == 204
    db.get(DeliveryShareLink, uuid.UUID(expired["id"])).expires_at = utcnow() - timedelta(minutes=1)
    db.commit()
    responses = [http.get(f"/api/v1/public/track/{t}") for t in (
        _token(revoked["url"]), _token(expired["url"]), "x" * 43, "short")]
    assert {r.status_code for r in responses} == {404}
    # Identical code and message (only the per-request id differs): no enumeration signal.
    assert len({(r.json()["error"]["code"], r.json()["error"]["message"]) for r in responses[:3]}) == 1


def test_links_stop_working_after_delivery_and_cannot_be_made_for_closed_orders(shared, monkeypatch):
    http, db, order = shared["http"], shared["db"], shared["order"]
    token = _token(http.post(f"/api/v1/orders/{order.id}/share-links", json={}).json()["url"])
    order.status, order.delivered_at = "delivered", (utcnow() - timedelta(hours=1)).replace(tzinfo=None)
    db.commit()
    assert http.get(f"/api/v1/public/track/{token}").status_code == 200  # still within 48 h
    order.delivered_at = (utcnow() - timedelta(hours=settings.TRACKING_LINK_AFTER_DELIVERY_HOURS + 1)).replace(tzinfo=None)
    db.commit()
    assert http.get(f"/api/v1/public/track/{token}").status_code == 404
    order.status = "cancelled"
    db.commit()
    assert http.post(f"/api/v1/orders/{order.id}/share-links", json={}).status_code == 409


def test_creating_beyond_the_limit_revokes_the_oldest(shared, monkeypatch):
    http, order = shared["http"], shared["order"]
    monkeypatch.setattr(settings, "TRACKING_LINK_MAX_ACTIVE", 2)
    first = http.post(f"/api/v1/orders/{order.id}/share-links", json={}).json()
    http.post(f"/api/v1/orders/{order.id}/share-links", json={})
    http.post(f"/api/v1/orders/{order.id}/share-links", json={})
    assert http.get(f"/api/v1/public/track/{_token(first['url'])}").status_code == 404
    links = http.get(f"/api/v1/orders/{order.id}/share-links").json()
    assert sum(1 for link in links if link["active"]) == 2


def test_public_tracking_is_rate_limited(shared):
    http = shared["http"]
    statuses = [http.get(f"/api/v1/public/track/{'y' * 43}").status_code for _ in range(31)]
    assert statuses[:30] == [404] * 30 and statuses[30] == 429
