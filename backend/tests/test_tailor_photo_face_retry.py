"""Tailor and designer avatar updates are not NIN verification operations."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.user_service import UserService


@pytest.mark.parametrize("role", ["tailor", "designer", "vendor", "delivery_partner", "customer"])
def test_photo_update_skips_face_check_for_tailors_and_designers(role):
    user = SimpleNamespace(
        id="user-1", role=role, full_name="Test Person",
        profile_photo_url="/media/old.jpg",
    )
    db = MagicMock()
    repository = MagicMock()
    repository.get_by_id.return_value = user
    service = UserService(db)
    service.users = repository

    with (patch("app.services.kyc_service.KYCService.check_new_profile_photo") as check,
          patch("app.services.verification_documents.read_profile_photo", return_value=b"valid-photo")):
        result = service.update_profile(user.id, profile_photo_url="/media/new.jpg")

    assert result.profile_photo_url == "/media/new.jpg"
    assert db.commit.call_count == 1
    if role in {"tailor", "designer"}:
        check.assert_not_called()
    else:
        check.assert_called_once()


@pytest.mark.parametrize("role", ["tailor", "designer"])
def test_professional_photo_update_does_not_need_face_provider(role):
    user = SimpleNamespace(
        id="professional-1", role=role, full_name="Test Professional",
        profile_photo_url=None,
    )
    db = MagicMock()
    service = UserService(db)
    service.users = MagicMock()
    service.users.get_by_id.return_value = user
    with (patch("app.services.kyc_service.KYCService.check_new_profile_photo",
                side_effect=AssertionError("Face provider must not be invoked")),
          patch("app.services.verification_documents.read_profile_photo", return_value=b"valid-photo")):
        service.update_profile(user.id, profile_photo_url="/media/avatar.jpg")
    assert user.profile_photo_url == "/media/avatar.jpg"
