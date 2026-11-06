"""Logistics phase 7: baselines, backtested ETA calibration, advisory recommendations, optional AI."""
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.timezone import utcnow
from app.main import app
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.location import Location
from app.models.order import Order
from app.services.delivery_intelligence_service import RULESET_VERSION, DeliveryIntelligenceService


@pytest.fixture()
def history(db, make_user):
    """25 finished bike deliveries whose real trips took 1.5x the 30-minute route estimate."""
    seller, buyer = make_user(role="tailor"), make_user()
    user = make_user(role="delivery_partner", full_name="Sola Bello")
    partner = DeliveryPartner(user_id=user.id, is_verified=True, is_available=True, vehicle_type="bike")
    db.add(partner)
    db.flush()
    for i in range(25):
        pickup = Location(location_type="delivery_pickup", latitude=6.51, longitude=3.37)
        dropoff = Location(location_type="delivery_dropoff", latitude=6.45, longitude=3.47)
        order = Order(order_number=f"AI-{uuid.uuid4().hex[:8]}", order_type="customer_order", buyer_user_id=buyer.id,
                      seller_user_id=seller.id, status="delivered", subtotal=1, total_amount=1, currency="NGN",
                      ordered_at=utcnow())
        db.add_all([pickup, dropoff, order])
        db.flush()
        start = utcnow() - timedelta(days=20 - i % 20, hours=2)
        req = DeliveryRequest(order_id=order.id, pickup_location_id=pickup.id, dropoff_location_id=dropoff.id,
                              status="assigned", route_duration_minutes=30, route_source="osrm", created_at=start)
        db.add(req)
        db.flush()
        picked = start + timedelta(minutes=10)
        db.add(Delivery(order_id=order.id, delivery_request_id=req.id, status="delivered", provider="internal",
                        delivery_fee=1000, delivery_partner_id=partner.id, created_at=start + timedelta(minutes=i),
                        picked_up_at=picked.replace(tzinfo=None), delivered_at=(picked + timedelta(minutes=45 + i % 3)).replace(tzinfo=None)))
    db.commit()
    return {"db": db, "partner": partner}


def test_calibration_learns_the_real_pace_and_beats_the_raw_estimate(history):
    report = DeliveryIntelligenceService(history["db"]).eta_calibration()
    bike = report["by_vehicle"]["bike"]
    assert bike["samples"] == 25 and 1.45 <= bike["factor"] <= 1.6 and bike["usable"] is True
    assert bike["backtest"]["mean_error_minutes_calibrated"] < bike["backtest"]["mean_error_minutes_raw"]
    assert report["version"] == RULESET_VERSION and report["enabled"] is False


def test_calibration_changes_etas_only_when_switched_on(history, monkeypatch):
    service = DeliveryIntelligenceService(history["db"])
    assert service.calibrated_minutes(20, "bike") == (20, False)
    monkeypatch.setattr(settings, "DELIVERY_ETA_CALIBRATION_ENABLED", True)
    minutes, applied = service.calibrated_minutes(20, "bike")
    assert applied and 29 <= minutes <= 32
    assert service.calibrated_minutes(20, "van") == (20, False)  # no validated data for vans


def test_readiness_reports_and_recommendations_carry_evidence(history):
    service = DeliveryIntelligenceService(history["db"])
    readiness = service.readiness()
    assert readiness["ready_for_models"] is False and "Baselines only" in readiness["message"]
    riders = service.rider_performance()
    assert riders[0]["first_name"] == "Sola" and riders[0]["deliveries"] == 25 and riders[0]["median_trip_minutes"] >= 45
    recs = service.recommendations()
    codes = {r["code"] for r in recs}
    assert "keep_baselines" in codes and "eta_calibration" in codes
    for rec in recs:
        assert rec["evidence"] and rec["reasoning"] and rec["version"] == RULESET_VERSION
        assert rec["advisory"] is True and rec["generated_at"] and rec["confidence"] in {"low", "medium", "high"}
    assert service.route_efficiency()["trips_measured"] == 25


def test_summary_works_without_ai_and_uses_ai_only_when_enabled(history, monkeypatch):
    service = DeliveryIntelligenceService(history["db"])
    plain = service.summary()
    assert plain["source"] == "rules" and "deliveries completed" in plain["summary"]
    from app.integrations.ai import llm_client

    class Reply:
        content = "Riders are taking about half again as long as estimated."
    monkeypatch.setattr(settings, "DELIVERY_AI_SUMMARIES_ENABLED", True)
    monkeypatch.setattr(llm_client.LLMClient, "complete", lambda self, messages, max_tokens=512: Reply())
    assert service.summary()["source"].startswith("ai:")

    def broken(self, messages, max_tokens=512):
        raise RuntimeError("provider down")
    monkeypatch.setattr(llm_client.LLMClient, "complete", broken)
    assert service.summary()["source"] == "rules"  # AI failure never breaks insights


def test_insights_are_admin_only(history, make_user):
    db = history["db"]
    current = [make_user(role="admin")]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    try:
        with TestClient(app) as http:
            body = http.get("/api/v1/admin/dispatch/insights").json()
            assert set(body) == {"readiness", "eta_calibration", "riders", "demand", "routes", "recommendations", "summary"}
            current[0] = make_user()
            assert http.get("/api/v1/admin/dispatch/insights").status_code == 403
    finally:
        app.dependency_overrides.clear()
