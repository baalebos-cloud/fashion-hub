"""Hackathon visibility must not falsely verify or expose private photos."""
import uuid

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.professional import Professional
from app.models.design_image import DesignImage
from app.models.stored_media import StoredMedia


def test_pending_registered_professional_visible_only_with_demo_gate(db, make_user, monkeypatch):
    seller = make_user(role="tailor")
    profile = Professional(user_id=seller.id, professional_type="tailor",
                           business_name="Demo Studio", is_verified=False)
    db.add(profile)
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            monkeypatch.setattr(settings, "HACKATHON_SHOW_PENDING_PROFESSIONALS", False)
            assert client.get("/api/v1/professionals").json()["total"] == 0
            assert client.get(f"/api/v1/professionals/{profile.id}").status_code == 404
            monkeypatch.setattr(settings, "HACKATHON_SHOW_PENDING_PROFESSIONALS", True)
            listed = client.get("/api/v1/professionals")
            assert listed.status_code == 200
            assert listed.json()["total"] == 1
            assert listed.json()["items"][0]["is_verified"] is False
            assert client.get(f"/api/v1/professionals/{profile.id}").status_code == 200
            seller.is_active = False
            db.commit()
            assert client.get("/api/v1/professionals").json()["total"] == 0
            assert client.get(f"/api/v1/professionals/{profile.id}").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_public_gallery_returns_only_public_owned_portfolio_media(db, make_user, monkeypatch):
    seller = make_user(role="designer")
    profile = Professional(user_id=seller.id, professional_type="designer",
                           business_name="Design Gallery", is_verified=False)
    db.add(profile)
    db.flush()
    good_id, private_id = uuid.uuid4(), uuid.uuid4()
    db.add_all([
        StoredMedia(id=good_id, owner_user_id=seller.id,
                    storage_key=f"portfolio/{seller.id}/safe.jpg",
                    is_public=True, content_type="image/jpeg", content=b"abc"),
        StoredMedia(id=private_id, owner_user_id=seller.id,
                    storage_key=f"kyb/{seller.id}/private.jpg",
                    is_public=False, content_type="image/jpeg", content=b"secret"),
        DesignImage(professional_id=profile.id,
                    image_url=f"https://old.example/api/v1/media/files/{good_id}"),
        DesignImage(professional_id=profile.id,
                    image_url=f"https://old.example/api/v1/media/files/{private_id}"),
    ])
    db.commit()
    monkeypatch.setattr(settings, "HACKATHON_SHOW_PENDING_PROFESSIONALS", True)
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/professionals/{profile.id}/portfolio")
            assert response.status_code == 200
            assert len(response.json()) == 1
            assert str(good_id) in response.json()[0]["image_url"]
            assert str(private_id) not in str(response.json())
    finally:
        app.dependency_overrides.clear()
