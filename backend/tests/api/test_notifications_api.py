"""In-app notifications cannot leak another user's events or auth-email outbox."""
import uuid

from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.notification import Notification


def test_notification_feed_is_paginated_in_app_only_and_owner_scoped(db, make_user):
    owner, other = make_user(), make_user()
    owned = Notification(recipient_user_id=owner.id, channel="in_app",
                         event_type="order.completed", title="Done", body="Order completed")
    foreign = Notification(recipient_user_id=other.id, channel="in_app",
                           event_type="order.completed", title="Another user's event", body="Private")
    email = Notification(recipient_user_id=owner.id, channel="email",
                         event_type="auth.password_reset", title="Reset", body="Pending",
                         metadata_json={"ciphertext": "secret"})
    db.add_all([owned, foreign, email])
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: owner
    try:
        with TestClient(app) as client:
            url = "/api/v1/notifications"
            response = client.get(url)
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["total"] == 1 and data["page"] == 1
            assert data["items"][0]["id"] == str(owned.id)
            assert "metadata_json" not in data["items"][0]
            assert client.get(url, params={"unread_only": True}).json()["total"] == 1
            assert client.get(url, params={"page_size": 0}).status_code == 422
            assert client.post(f"{url}/{foreign.id}/read").status_code == 404
            assert client.post(f"{url}/{email.id}/read").status_code == 404
            assert client.post(f"{url}/{uuid.uuid4()}/read").status_code == 404
            assert client.post(f"{url}/{owned.id}/read").status_code == 204
            assert client.post(f"{url}/{owned.id}/read").status_code == 204
            assert client.get(url, params={"unread_only": True}).json()["items"] == []
            db.refresh(foreign)
            assert foreign.is_read is False
    finally:
        app.dependency_overrides.clear()
