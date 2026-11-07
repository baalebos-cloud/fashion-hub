"""Recommendations PR 1: shopping activity recording, opt-out, retention and history sync."""
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user
from app.core.rate_limit import limiter
from app.core.timezone import utcnow
from app.main import app
from app.models.activity_log import ActivityLog
from app.models.design import Design
from app.models.favorite import Favorite
from app.models.interaction_event import InteractionEvent
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.professional import Professional
from app.services import interaction_service
from app.services.cart_service import CartService
from tests import vendor_helpers

EVENTS = "/api/v1/interactions/events"


@pytest.fixture()
def client(db):
    limiter.reset()
    current = [None]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    app.dependency_overrides[get_optional_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield http, current
    app.dependency_overrides.clear()


def _design(db, make_user):
    tailor = make_user(role="tailor")
    professional = Professional(user_id=tailor.id, professional_type="tailor", is_verified=True)
    db.add(professional)
    db.flush()
    design = Design(professional_id=professional.id, title="Agbada", description="Hand finished",
                    base_price=Decimal("45000"), required_measurement_fields=["chest"], is_published=True)
    db.add(design)
    db.commit()
    return tailor, professional, design


def _events(db, **filters):
    return db.query(InteractionEvent).filter_by(**filters).all()


def test_signed_in_views_and_searches_are_recorded_without_ip(db, make_user, client):
    http, current = client
    current[0] = make_user()
    _, professional, design = _design(db, make_user)
    response = http.post(EVENTS, json={"events": [
        {"event_type": "view", "item_type": "design", "item_id": str(design.id), "source": "product_page"},
        {"event_type": "view", "item_type": "professional", "item_id": str(professional.id)},
        {"event_type": "search", "search_query": "  Blue   AGBADA under 50k ", "source": "search_results"},
    ]})
    assert response.status_code == 202, response.text
    assert response.json() == {"accepted": 3}
    rows = _events(db, user_id=current[0].id)
    assert {r.event_type for r in rows} == {"view", "search"}
    assert next(r for r in rows if r.event_type == "search").search_query == "blue agbada under 50k"
    assert next(r for r in rows if r.item_id == design.id).source == "product_page"
    # Activity batches never reach the admin activity log, which stores IP addresses.
    assert db.query(ActivityLog).filter(ActivityLog.path.like("/api/v1/interactions%")).count() == 0


def test_signed_out_visitors_need_a_browser_id(db, make_user, client):
    http, _ = client
    _, _, design = _design(db, make_user)
    event = {"event_type": "view", "item_type": "design", "item_id": str(design.id)}
    assert http.post(EVENTS, json={"events": [event]}).json() == {"accepted": 0}
    browser = str(uuid.uuid4())
    assert http.post(EVENTS, json={"anonymous_id": browser, "events": [event]}).json() == {"accepted": 1}
    (row,) = _events(db, anonymous_id=browser)
    assert row.user_id is None


def test_browser_cannot_report_purchases_cart_adds_or_favourites(db, make_user, client):
    http, current = client
    current[0] = make_user()
    _, _, design = _design(db, make_user)
    for kind in ("purchase", "add_to_cart", "favorite"):
        response = http.post(EVENTS, json={"events": [
            {"event_type": kind, "item_type": "design", "item_id": str(design.id)}]})
        assert response.status_code == 422
    assert _events(db, user_id=current[0].id) == []


def test_unknown_items_and_repeat_views_are_dropped(db, make_user, client):
    http, current = client
    current[0] = make_user()
    _, _, design = _design(db, make_user)
    view = {"event_type": "view", "item_type": "design", "item_id": str(design.id)}
    ghost = {"event_type": "view", "item_type": "product", "item_id": str(uuid.uuid4())}
    assert http.post(EVENTS, json={"events": [view, view, ghost]}).json() == {"accepted": 1}
    assert http.post(EVENTS, json={"events": [view]}).json() == {"accepted": 0}
    # After the 30-minute window a new view counts again.
    db.query(InteractionEvent).update({InteractionEvent.occurred_at: utcnow() - timedelta(minutes=31)})
    db.commit()
    assert http.post(EVENTS, json={"events": [view]}).json() == {"accepted": 1}


def test_batches_are_capped(db, make_user, client):
    http, current = client
    current[0] = make_user()
    too_many = [{"event_type": "search", "search_query": f"q{i}"} for i in range(51)]
    assert http.post(EVENTS, json={"events": too_many}).status_code == 422


def test_turning_personalisation_off_stops_recording_and_deletes_history(db, make_user, client):
    http, current = client
    current[0] = make_user()
    _, _, design = _design(db, make_user)
    view = {"event_type": "view", "item_type": "design", "item_id": str(design.id)}
    assert http.post(EVENTS, json={"events": [view]}).json() == {"accepted": 1}
    assert http.get("/api/v1/interactions/preference").json() == {"personalization_enabled": True}

    response = http.put("/api/v1/interactions/preference", json={"personalization_enabled": False})
    assert response.json() == {"personalization_enabled": False}
    assert _events(db, user_id=current[0].id) == []
    db.query(InteractionEvent).delete()
    db.commit()
    assert http.post(EVENTS, json={"events": [view]}).json() == {"accepted": 0}

    http.put("/api/v1/interactions/preference", json={"personalization_enabled": True})
    assert http.post(EVENTS, json={"events": [view]}).json() == {"accepted": 1}


def test_old_activity_is_purged(db, make_user):
    user = make_user()
    old = InteractionEvent(user_id=user.id, event_type="search", search_query="old",
                           occurred_at=utcnow() - timedelta(days=settings.INTERACTION_RETENTION_DAYS + 1))
    fresh = InteractionEvent(user_id=user.id, event_type="search", search_query="new", occurred_at=utcnow())
    db.add_all([old, fresh])
    db.commit()
    assert interaction_service.purge_expired(db) == 1
    assert [r.search_query for r in _events(db, user_id=user.id)] == ["new"]


def _order(db, buyer, seller, *, status="received"):
    order = Order(order_number="TL-" + uuid.uuid4().hex[:10], order_type="customer_order",
                  buyer_user_id=buyer.id, seller_user_id=seller.id, status=status,
                  subtotal=0, total_amount=0, ordered_at=utcnow())
    db.add(order)
    db.flush()
    return order


def test_history_sync_copies_favourites_cart_adds_and_purchases_once(db, make_user):
    buyer, opted_out = make_user(), make_user(personalization_enabled=False)
    material_buyer = make_user(role="designer")  # carts are for tailors and designers buying materials
    tailor, professional, design = _design(db, make_user)
    _, _, product, variant, _ = vendor_helpers.catalog(db)

    db.add_all([Favorite(user_id=buyer.id, favorite_type="design", favorite_ref_id=design.id),
                Favorite(user_id=opted_out.id, favorite_type="design", favorite_ref_id=design.id)])
    db.commit()
    CartService(db).add_item(owner_user_id=material_buyer.id, product_variant_id=variant.id, quantity=1)

    bought = _order(db, buyer, tailor)
    db.add(OrderItem(order_id=bought.id, reference_type="design", reference_id=design.id,
                     name_snapshot="Agbada", unit_price=1, quantity=1, line_total=1))
    cancelled = _order(db, buyer, tailor, status="cancelled")
    db.add(OrderItem(order_id=cancelled.id, reference_type="design", reference_id=design.id,
                     name_snapshot="Agbada", unit_price=1, quantity=1, line_total=1))
    db.commit()

    assert interaction_service.sync_history(db) == 4
    assert interaction_service.sync_history(db) == 0  # safe to re-run
    rows = {(r.event_type, r.item_type, r.item_id) for r in _events(db, user_id=buyer.id)}
    assert rows == {("favorite", "design", design.id), ("purchase", "design", design.id),
                    ("purchase", "professional", professional.id)}
    (cart_add,) = _events(db, user_id=material_buyer.id)
    assert (cart_add.event_type, cart_add.item_type, cart_add.item_id) == ("add_to_cart", "product", product.id)
    assert all(r.source == "history" for r in _events(db, user_id=buyer.id))
    assert _events(db, user_id=opted_out.id) == []
