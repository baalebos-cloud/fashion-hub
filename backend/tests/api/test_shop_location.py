"""Saving a shop pin keeps the readable address and area used on the public shop page."""
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.location import Location
from app.models.professional import Professional


def test_shop_location_keeps_address_city_and_state(db, make_user):
    tailor = make_user(role="tailor")
    profile = Professional(user_id=tailor.id, professional_type="tailor", business_name="Ado Stitches")
    db.add(profile)
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: tailor
    try:
        with TestClient(app) as http:
            response = http.patch("/api/v1/professionals/me/location", params={
                "latitude": 7.64036, "longitude": 5.22103,
                "formatted_address": "  14 Iworoko Road, Ado-Ekiti  ", "city": "Ado-Ekiti",
                "state_region": "Ekiti", "country": "Nigeria"})
            assert response.status_code == 200, response.text
            db.refresh(profile)
            location = db.get(Location, profile.location_id)
            assert location.formatted_address == "14 Iworoko Road, Ado-Ekiti"
            assert (location.city, location.state_region, location.country) == ("Ado-Ekiti", "Ekiti", "Nigeria")
            from sqlalchemy import text
            wkt = db.execute(text("SELECT ST_AsText(geom) FROM locations WHERE id = :id"), {"id": location.id}).scalar()
            assert wkt == "POINT(5.22103 7.64036)"  # proximity search needs geom

            pin_only = http.patch("/api/v1/professionals/me/location",
                                  params={"latitude": 7.6, "longitude": 5.2, "city": "   "})
            assert pin_only.status_code == 200
            db.refresh(profile)
            assert db.get(Location, profile.location_id).city is None
    finally:
        app.dependency_overrides.clear()
