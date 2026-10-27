"""Fresh customer and courier onboarding: only admins can verify courier accounts."""
import uuid

from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.customer import Customer
from app.models.measurement_profile import MeasurementProfile


def test_customer_profile_is_created_once_and_default_measurement_is_owned(db, make_user):
    owner, other, courier = make_user(), make_user(), make_user(role="delivery_partner")
    current = [owner]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    try:
        with TestClient(app) as http:
            one = http.get("/api/v1/customers/me")
            two = http.get("/api/v1/customers/me")
            assert one.status_code == two.status_code == 200
            assert one.json()["id"] == two.json()["id"]
            assert one.json()["preferred_currency"] == "NGN"
            profile = MeasurementProfile(customer_id=uuid.UUID(one.json()["id"]), label="My measurements")
            db.add(profile)
            db.commit()
            selected = http.patch("/api/v1/customers/me", json={
                "default_measurement_profile_id": str(profile.id),
            })
            assert selected.status_code == 200, selected.text
            assert selected.json()["default_measurement_profile_id"] == str(profile.id)
            current[0] = other
            assert http.patch("/api/v1/customers/me", json={
                "default_measurement_profile_id": str(profile.id),
            }).status_code == 403
            current[0] = courier
            assert http.get("/api/v1/customers/me").status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_courier_registration_and_admin_verification(db, make_user):
    rider, outsider, admin = (
        make_user(role="delivery_partner"), make_user(), make_user(role="admin"))
    current = [rider]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    try:
        with TestClient(app) as http:
            one = http.get("/api/v1/delivery-partners/me")
            assert one.status_code == 200, one.text
            assert one.json()["is_verified"] is False
            assert one.json()["is_available"] is False
            assert http.put("/api/v1/delivery-partners/me/availability",
                            json={"is_available": True}).status_code == 409
            saved = http.put("/api/v1/delivery-partners/me", json={"vehicle_type": "bike"})
            assert saved.status_code == 200, saved.text
            current[0] = outsider
            assert http.get("/api/v1/delivery-partners/me").status_code == 403
            assert http.post(f"/api/v1/delivery-partners/{one.json()['id']}/verify").status_code == 403
            current[0] = admin
            verified = http.post(f"/api/v1/delivery-partners/{one.json()['id']}/verify")
            assert verified.status_code == 200, verified.text
            assert verified.json()["is_verified"] is True
            current[0] = rider
            assert http.put("/api/v1/delivery-partners/me/availability",
                            json={"is_available": True}).json()["is_available"] is True
            # Changing the vehicle disables an existing verified rider, pending re-review.
            changed = http.put("/api/v1/delivery-partners/me", json={"vehicle_type": "van"})
            assert changed.status_code == 200
            assert changed.json()["is_verified"] is False
            assert changed.json()["is_available"] is False
    finally:
        app.dependency_overrides.clear()
