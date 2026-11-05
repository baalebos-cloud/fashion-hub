"""Phase 2: admin cancel / release / reassign and rider issue handling, with audit trail."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.audit_log import AuditLog
from app.models.delivery import Delivery
from app.models.delivery_offer import DeliveryOffer
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.location import Location
from app.models.notification import Notification
from app.models.order_timeline import OrderTimelineEntry
from app.models.professional import Professional
from app.services.order_service import OrderService
from tests.catalog_helpers import catalog_request

REASON = {"reason": "Rider not responding for 40 minutes"}


@pytest.fixture()
def board(db, make_user):
    buyer, seller, admin = make_user(), make_user(role="tailor"), make_user(role="admin")
    rider_a = make_user(role="delivery_partner", full_name="Sola Bello")
    rider_b = make_user(role="delivery_partner", full_name="Tayo Ade")
    rider_off = make_user(role="delivery_partner", full_name="Offline Rider")
    order = OrderService(db).create_customer_order(**catalog_request(db, buyer, seller))
    shop = Location(location_type="tailor_shop", formatted_address="12 Shop Rd", city="Ikeja",
                    state_region="Lagos", latitude=6.6, longitude=3.35)
    db.add(shop)
    db.flush()
    db.query(Professional).filter_by(user_id=seller.id).one().location_id = shop.id
    order.status = "ready_for_delivery"
    pa = DeliveryPartner(user_id=rider_a.id, is_verified=True, is_available=True, vehicle_type="bike")
    pb = DeliveryPartner(user_id=rider_b.id, is_verified=True, is_available=True, vehicle_type="car")
    poff = DeliveryPartner(user_id=rider_off.id, is_verified=True, is_available=False, vehicle_type="bike")
    db.add_all([pa, pb, poff])
    db.commit()
    current = [seller]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        request_id = http.post(f"/api/v1/delivery-requests/orders/{order.id}").json()["id"]
        current[0] = rider_a
        delivery_id = http.post(f"/api/v1/delivery-requests/{request_id}/accept").json()["id"]
        current[0] = admin
        yield {"http": http, "current": current, "db": db, "order": order, "buyer": buyer, "seller": seller,
               "admin": admin, "rider_a": rider_a, "rider_b": rider_b, "pa": pa, "pb": pb, "poff": poff,
               "request_id": request_id, "delivery_id": delivery_id}
    app.dependency_overrides.clear()


def test_release_puts_the_job_back_and_revokes_the_old_rider(board):
    http, current, db = board["http"], board["current"], board["db"]
    delivery_id = board["delivery_id"]
    assert http.post(f"/api/v1/admin/dispatch/deliveries/{delivery_id}/release", json={"reason": "no"}).status_code == 422
    released = http.post(f"/api/v1/admin/dispatch/deliveries/{delivery_id}/release", json=REASON)
    assert released.status_code == 200, released.text
    new_request_id = released.json()["request_id"]

    old = db.get(Delivery, uuid.UUID(delivery_id))
    assert old.status == "cancelled" and db.get(DeliveryRequest, uuid.UUID(board["request_id"])).status == "cancelled"
    assert db.get(DeliveryPartner, board["pa"].id).is_available is False
    assert board["order"].status == "ready_for_delivery"  # the seller isn't penalised
    audit = db.query(AuditLog).filter_by(action="dispatch.released").one()
    assert audit.actor_user_id == board["admin"].id and audit.metadata_json["reason"] == REASON["reason"]
    assert db.query(OrderTimelineEntry).filter(OrderTimelineEntry.note.like("Dispatch released%")).count() == 1
    assert db.query(Notification).filter_by(recipient_user_id=board["rider_a"].id, event_type="dispatch.released").count() == 1

    current[0] = board["rider_a"]  # released rider loses the route and contacts immediately
    assert http.get(f"/api/v1/deliveries/{delivery_id}/trip").status_code == 404
    assert http.post(f"/api/v1/deliveries/{delivery_id}/picked-up").status_code in {404, 409}
    current[0] = board["rider_b"]  # the job is back on the board and can be claimed again
    assert any(j["id"] == new_request_id for j in http.get("/api/v1/delivery-requests/available").json())
    claimed = http.post(f"/api/v1/delivery-requests/{new_request_id}/accept")
    assert claimed.status_code == 200, claimed.text
    current[0] = board["buyer"]
    tracking = http.get(f"/api/v1/deliveries/orders/{board['order'].id}/tracking").json()
    assert tracking["id"] == claimed.json()["id"] and tracking["rider_name"] == "Tayo Ade"


def test_reassign_moves_the_job_to_a_chosen_online_rider(board):
    http, db, delivery_id = board["http"], board["db"], board["delivery_id"]
    url = f"/api/v1/admin/dispatch/deliveries/{delivery_id}/reassign"
    assert http.post(url, json={**REASON, "partner_id": str(board["poff"].id)}).status_code == 409  # offline
    assert http.post(url, json={**REASON, "partner_id": str(board["pa"].id)}).status_code == 409  # same rider
    riders = http.get("/api/v1/admin/dispatch/riders").json()
    assert {r["first_name"] for r in riders} == {"Tayo"}  # Sola is busy with this job, Offline Rider is offline
    moved = http.post(url, json={**REASON, "partner_id": str(board["pb"].id)})
    assert moved.status_code == 200, moved.text
    new = db.get(Delivery, uuid.UUID(moved.json()["delivery_id"]))
    old = db.get(Delivery, uuid.UUID(delivery_id))
    assert new.delivery_partner_id == board["pb"].id and new.status == "assigned"
    assert float(new.delivery_fee) == float(old.delivery_fee) and old.status == "cancelled"
    assert db.get(DeliveryPartner, board["pb"].id).is_available is False  # now busy
    assert db.query(AuditLog).filter_by(action="dispatch.reassigned").count() == 1
    assert db.query(Notification).filter_by(recipient_user_id=board["rider_b"].id, event_type="dispatch.assigned").count() == 1


def test_collected_packages_cannot_be_released(board):
    http, current, delivery_id = board["http"], board["current"], board["delivery_id"]
    current[0] = board["rider_a"]
    assert http.post(f"/api/v1/deliveries/{delivery_id}/picked-up").status_code == 200
    current[0] = board["admin"]
    response = http.post(f"/api/v1/admin/dispatch/deliveries/{delivery_id}/release", json=REASON)
    assert response.status_code == 409 and "issue workflow" in response.text


def test_cancel_search_declines_offers_and_seller_can_request_again(board, make_user):
    http, current, db = board["http"], board["current"], board["db"]
    released = http.post(f"/api/v1/admin/dispatch/deliveries/{board['delivery_id']}/release", json=REASON).json()
    request_id = released["request_id"]
    current[0] = board["rider_b"]
    job = next(j for j in http.get("/api/v1/delivery-requests/available").json() if j["id"] == request_id)
    http.post(f"/api/v1/delivery-requests/{request_id}/offers",
              json={"amount": job["suggested_fare"], "eta_to_pickup_minutes": 5})
    current[0] = board["admin"]
    assert http.post(f"/api/v1/admin/dispatch/requests/{request_id}/cancel",
                     json={"reason": "Seller asked to hold the order"}).status_code == 200
    assert http.post(f"/api/v1/admin/dispatch/requests/{request_id}/cancel", json=REASON).status_code == 409
    assert db.query(DeliveryOffer).filter_by(delivery_request_id=uuid.UUID(request_id)).one().status == "declined"
    current[0] = board["seller"]
    again = http.post(f"/api/v1/delivery-requests/orders/{board['order'].id}")
    assert again.status_code == 201 and again.json()["id"] != request_id and again.json()["status"] == "requested"


def test_issue_reports_reach_admins_and_need_a_resolution_note(board):
    http, current, db, delivery_id = board["http"], board["current"], board["db"], board["delivery_id"]
    current[0] = board["rider_a"]
    issue_id = http.post(f"/api/v1/deliveries/{delivery_id}/issues", json={
        "issue_type": "WRONG_ADDRESS", "description": "Gate number doesn't exist"}).json()["id"]
    current[0] = board["admin"]
    board_view = http.get("/api/v1/admin/dispatch-board").json()
    row = next(a for a in board_view["active"] if a["id"] == delivery_id)
    assert board_view["open_issue_count"] == 1 and row["open_issue_count"] == 1
    assert row["rider_first_name"] == "Sola" and row["order_number"] == board["order"].order_number
    issues = http.get("/api/v1/admin/dispatch/issues").json()
    assert issues[0]["issue_type"] == "WRONG_ADDRESS" and issues[0]["rider_first_name"] == "Sola"
    url = f"/api/v1/admin/dispatch/issues/{issue_id}"
    assert http.patch(url, json={"status": "INVESTIGATING"}).json()["status"] == "INVESTIGATING"
    assert http.patch(url, json={"status": "RESOLVED"}).status_code == 422
    assert http.patch(url, json={"status": "RESOLVED", "note": "Customer shared the right gate"}).status_code == 200
    assert http.patch(url, json={"status": "INVESTIGATING"}).status_code == 409
    assert http.get("/api/v1/admin/dispatch/issues").json() == []
    assert db.query(Notification).filter_by(recipient_user_id=board["rider_a"].id,
                                            event_type="dispatch.issue_resolved").count() == 1


@pytest.mark.parametrize("role_key", ["seller", "buyer", "rider_a"])
def test_dispatch_controls_are_admin_only(board, role_key):
    http, current = board["http"], board["current"]
    current[0] = board[role_key]
    for method, url, body in [
        ("post", f"/api/v1/admin/dispatch/deliveries/{board['delivery_id']}/release", REASON),
        ("post", f"/api/v1/admin/dispatch/deliveries/{board['delivery_id']}/reassign", {**REASON, "partner_id": str(board["pb"].id)}),
        ("post", f"/api/v1/admin/dispatch/requests/{board['request_id']}/cancel", REASON),
        ("get", "/api/v1/admin/dispatch/issues", None), ("get", "/api/v1/admin/dispatch/riders", None),
    ]:
        response = getattr(http, method)(url, json=body) if body else getattr(http, method)(url)
        assert response.status_code == 403, (url, response.status_code)


def test_releasing_a_delivery_reroutes_its_open_issues(board):
    http, current, delivery_id = board["http"], board["current"], board["delivery_id"]
    current[0] = board["rider_a"]
    http.post(f"/api/v1/deliveries/{delivery_id}/issues", json={
        "issue_type": "VEHICLE_BREAKDOWN", "description": "Bike won't start"})
    current[0] = board["admin"]
    assert http.post(f"/api/v1/admin/dispatch/deliveries/{delivery_id}/release", json=REASON).status_code == 200
    assert http.get("/api/v1/admin/dispatch/issues").json() == []
    assert http.get("/api/v1/admin/dispatch-board").json()["open_issue_count"] == 0
