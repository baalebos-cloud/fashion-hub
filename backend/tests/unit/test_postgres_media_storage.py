"""PostgreSQL media storage: safe routing and access boundaries."""
import uuid
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException

from app.integrations.storage.object_storage import PostgresStorageProvider, get_storage_provider
from app.api.v1.media import view_media, view_private_media
from app.core.config import settings


def test_provider_selected_without_s3(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "postgres")
    assert isinstance(get_storage_provider(), PostgresStorageProvider)


def test_unauthenticated_private_media_never_exposed():
    doc = MagicMock()
    doc.is_public = False
    doc.storage_key = "kyc/owner/doc.pdf"
    db = MagicMock()
    db.get.return_value = doc
    with pytest.raises(HTTPException) as error:
        view_media(uuid.uuid4(), db=db)
    assert error.value.status_code == 404


def test_owner_or_admin_required_for_private_media():
    owner = uuid.uuid4()
    doc = MagicMock()
    doc.owner_user_id = owner
    doc.content = b"%PDF-test"
    doc.content_type = "application/pdf"
    db = MagicMock()
    db.get.return_value = doc
    stranger = MagicMock()
    stranger.id = uuid.uuid4()
    stranger.role = "customer"
    with pytest.raises(HTTPException) as error:
        view_private_media(uuid.uuid4(), user=stranger, db=db)
    assert error.value.status_code == 404
    allowed = MagicMock()
    allowed.id = owner
    allowed.role = "customer"
    response = view_private_media(uuid.uuid4(), user=allowed, db=db)
    assert response.body == doc.content
    assert response.headers["cache-control"] == "no-store"
