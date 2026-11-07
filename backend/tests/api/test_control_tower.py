"""Logistics phase 5: control tower exceptions, performance and riders (admin only)."""
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.timezone import utcnow
from app.main import app
from app.models.delivery import Delivery
from app.models.delivery_issue import DispatchIssueReport
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.location import Location
from app.models.order import Order
from app.services import delivery_position


@pytest.fixture()
def tower(db, make_user):
    seller, buyer, admin = make_user(role="tailor"), make_user(), make_user(role="admin")
    current = [admin]
    made = []

    def job(status="requested", minutes_ago=0, rider=None, picked_minutes_ago=None, route_minutes=None):
        pickup = Location(location_type="delivery_pickup", latitude=6.51, longitude=3.37)
        dropoff = Location(location_type="delivery_dropoff", latitude=6.45, longitude=3.47)
        order = Order(order_number="CT-" + uuid.uuid4().hex[:8].upper(), order_type="customer_order",
                      buyer_user_id=buyer.id, seller_user_id=seller.id, status="ready_for_delivery",
                      subtotal=1000, total_amount=1000, currency="NGN", ordered_at=utcnow())
        db.add_all([pickup, dropoff, order])
        db.flush()
        when = utcnow() - timedelta(minutes=minutes_ago)
        req = DeliveryRequest(order_id=order.id, pickup_location_id=pickup.id, dropoff_location_id=dropoff.id,
                              status="requested" if status == "requested" else "assigned", created_at=when,
                              route_duration_minutes=route_minutes)
        db.add(req)
        db.flush()
        delivery = None
        if status != "requested":
            delivery = Delivery(order_id=order.id, delivery_request_id=req.id, status=status, provider="internal",
                                delivery_fee=1000, delivery_partner_id=rider.id, created_at=when,
                                picked_up_at=(utcnow() - timedelta(minutes=picked_minutes_ago)).replace(tzinfo=None)
                                if picked_minutes_ago is not None else None)
            db.add(delivery)
        db.commit()
        made.append(delivery)
        return req, delivery

    def rider(name):
        user = make_user(role="delivery_partner", full_name=name)
        partner = DeliveryPartner(user_id=user.id, is_verified=True, is_available=False, vehicle_type="bike")
        db.add(partner)
        db.commit()
        return partner, user

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield {"http": http, "current": current, "job": job, "rider": rider, "db": db, "seller": seller}
    app.dependency_overrides.clear()
    for d in made:
        if d is not None:
            delivery_position.clear_position(d.id)


def _alerts(tower):
    body = tower["http"].get("/api/v1/admin/dispatch/control-tower").json()
    return body, {(a["type"], a["order_number"]) for a in body["exceptions"]}


def test_each_rule_fires_only_past_its_threshold(tower):
    sola, _ = tower["rider"]("Sola Bello")
    ada, _ = tower["rider"]("Ada Okafor")
    old_job, _ = tower["job"](minutes_ago=40)
    fresh_job, _ = tower["job"](minutes_ago=2)
    _, slow_pickup = tower["job"]("assigned", minutes_ago=45, rider=sola)
    _, on_time_pickup = tower["job"]("assigned", minutes_ago=5, rider=ada)
    _, late_trip = tower["job"]("in_transit", minutes_ago=120, rider=sola, picked_minutes_ago=80, route_minutes=30)
    _, fine_trip = tower["job"]("in_transit", minutes_ago=30, rider=ada, picked_minutes_ago=10, route_minutes=30)
    db = tower["db"]
    num = lambda obj: db.get(Order, obj.order_id).order_number  # noqa: E731
    body, alerts = _alerts(tower)
    assert ("unassigned_too_long", num(old_job)) in alerts and ("unassigned_too_long", num(fresh_job)) not in alerts
    assert ("pickup_delayed", num(slow_pickup)) in alerts and ("pickup_delayed", num(on_time_pickup)) not in alerts
    assert ("dropoff_delayed", num(late_trip)) in alerts and ("dropoff_delayed", num(fine_trip)) not in alerts
    assert ("tracking_lost", num(late_trip)) in alerts  # travelling 80 min, not sharing
    late = next(a for a in body["exceptions"] if a["type"] == "dropoff_delayed")
    assert "expected about 30 min" in late["message"] and late["action"] and late["rider"] == "Sola"
    severities = [a["severity"] for a in body["exceptions"]]
    assert severities == sorted(severities, key={"critical": 0, "warning": 1, "info": 2}.get)  # most urgent first
    assert "6.45" not in str(body) and "3.47" not in str(body)  # no coordinates


def test_off_route_location_off_and_rider_issues(tower):
    sola, sola_user = tower["rider"]("Sola Bello")
    _, wandering = tower["job"]("in_transit", minutes_ago=20, rider=sola, picked_minutes_ago=10)
    token = delivery_position.start_sharing(wandering.id)["share_token"]
    delivery_position.save_position(wandering.id, share_token=token, latitude=6.80, longitude=3.37, accuracy_m=10)
    ada, ada_user = tower["rider"]("Ada Okafor")
    _, dark = tower["job"]("in_transit", minutes_ago=20, rider=ada, picked_minutes_ago=10)
    token2 = delivery_position.start_sharing(dark.id)["share_token"]
    delivery_position.report_device_state(dark.id, share_token=token2, state="permission_denied")
    tower["db"].add(DispatchIssueReport(delivery_id=dark.id, courier_id=ada_user.id, issue_type="CUSTOMER_UNREACHABLE",
                                        description="Gate locked", status="OPEN"))
    tower["db"].commit()
    _, alerts = _alerts(tower)
    types = {t for t, _ in alerts}
    assert {"off_route", "location_off", "rider_issue"} <= types


def test_performance_and_riders_view(tower):
    sola, _ = tower["rider"]("Sola Bello")
    tower["rider"]("Idle Rider")
    _, done = tower["job"]("delivered", minutes_ago=60, rider=sola, picked_minutes_ago=40)
    done.delivered_at = utcnow().replace(tzinfo=None)
    tower["db"].commit()
    body, _ = _alerts(tower)
    perf = body["performance"]
    assert perf["delivered"] >= 1 and perf["median_trip_minutes"] is not None
    riders = tower["http"].get("/api/v1/admin/dispatch/riders/overview").json()
    names = {r["first_name"]: r for r in riders}
    assert names["Idle"]["state"] == "offline" and names["Idle"]["active_jobs"] == 0


def test_only_admins_see_the_control_tower(tower):
    tower["current"][0] = tower["seller"]
    assert tower["http"].get("/api/v1/admin/dispatch/control-tower").status_code == 403
    assert tower["http"].get("/api/v1/admin/dispatch/riders/overview").status_code == 403
