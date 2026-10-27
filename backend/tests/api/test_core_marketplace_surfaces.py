"""Production API contracts for marketplace search, messages, favorites and dashboards."""
import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.timezone import utcnow
from app.main import app
from app.models.order import Order
from app.models.professional import Professional


def test_search_hides_unverified_professionals_and_uses_real_rows(db, make_user):
    user = make_user(role="tailor")
    profile = Professional(user_id=user.id, professional_type="tailor",
                           business_name="Island Atelier", is_verified=False)
    db.add(profile)
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as http:
            assert http.get("/api/v1/search/professionals?q=Atelier").json() == []
            profile.is_verified = True
            db.commit()
            response = http.get("/api/v1/search/professionals?q=Atelier")
            assert response.status_code == 200, response.text
            assert len(response.json()) == 1
            assert response.json()[0]["business_name"] == "Island Atelier"
            assert http.get("/api/v1/search/professionals?q=x&lat=6.1").status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_order_messaging_enforces_participant_ownership(db, make_user):
    buyer = make_user(role="customer")
    seller = make_user(role="tailor")
    stranger = make_user(role="customer")
    order = Order(order_number="MSG-" + uuid.uuid4().hex[:18], order_type="customer_order",
                  buyer_user_id=buyer.id, seller_user_id=seller.id, status="pending",
                  subtotal=Decimal("100"), total_amount=Decimal("100"), currency="NGN",
                  ordered_at=utcnow())
    db.add(order)
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    current = [buyer]
    app.dependency_overrides[get_current_user] = lambda: current[0]
    try:
        with TestClient(app) as http:
            created = http.post("/api/v1/messages/conversations", json={"order_id": str(order.id)})
            assert created.status_code == 201, created.text
            cid = created.json()["id"]
            assert http.post("/api/v1/messages/conversations", json={"order_id": str(order.id)}).json()["id"] == cid
            sent = http.post(f"/api/v1/messages/conversations/{cid}/messages", json={"body": "Order details?"})
            assert sent.status_code == 201, sent.text
            assert http.get(f"/api/v1/messages/conversations/{cid}/messages").json()[0]["body"] == "Order details?"
            current[0] = seller
            assert len(http.get("/api/v1/messages/conversations").json()) == 1
            assert len(http.get(f"/api/v1/messages/conversations/{cid}/messages").json()) == 1
            current[0] = stranger
            assert http.get(f"/api/v1/messages/conversations/{cid}/messages").status_code == 403
            assert http.post(f"/api/v1/messages/conversations/{cid}/messages", json={"body": "Nope"}).status_code == 403
            assert http.post("/api/v1/messages/conversations", json={"order_id": str(order.id)}).status_code == 403
            assert http.get("/api/v1/messages/conversations").json() == []
    finally:
        app.dependency_overrides.clear()


def test_favorites_require_a_visible_listing_and_scope_to_the_owner(db, make_user):
    owner = make_user(role="customer")
    stranger = make_user(role="customer")
    seller = make_user(role="designer")
    professional = Professional(user_id=seller.id, professional_type="designer",
                                business_name="Fav Atelier", is_verified=True)
    db.add(professional)
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    current = [owner]
    app.dependency_overrides[get_current_user] = lambda: current[0]
    try:
        with TestClient(app) as http:
            payload = {"favorite_type": "professional", "favorite_ref_id": str(professional.id)}
            assert http.post("/api/v1/favorites", json=payload).json() == {"favorited": True}
            assert len(http.get("/api/v1/favorites").json()) == 1
            current[0] = stranger
            assert http.get("/api/v1/favorites").json() == []
            assert http.post("/api/v1/favorites", json={**payload, "favorite_ref_id": str(uuid.uuid4())}).status_code == 404
            current[0] = owner
            assert http.post("/api/v1/favorites", json=payload).json() == {"favorited": False}
    finally:
        app.dependency_overrides.clear()


def test_dashboard_scope_is_user_bound(db, make_user):
    owner = make_user(role="customer")
    stranger = make_user(role="customer")
    seller = make_user(role="tailor")
    db.add(Order(order_number="DB-" + uuid.uuid4().hex[:18], order_type="customer_order",
                 buyer_user_id=owner.id, seller_user_id=seller.id, status="pending",
                 subtotal=Decimal("25"), total_amount=Decimal("25"), currency="NGN",
                 ordered_at=utcnow()))
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    current = [owner]
    app.dependency_overrides[get_current_user] = lambda: current[0]
    try:
        with TestClient(app) as http:
            a = http.get("/api/v1/dashboard").json()
            assert a[0]["value"] == 1
            current[0] = stranger
            assert http.get("/api/v1/dashboard").json()[0]["value"] == 0
            current[0] = seller
            assert http.get("/api/v1/dashboard").json()[0]["value"] == 1
    finally:
        app.dependency_overrides.clear()
