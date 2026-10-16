"""Unit tests for AuthService: signup validation, login, password reset flow."""
import pytest

from app.core.exceptions import ConflictError, UnauthorizedError
from app.services.auth_service import AuthService


def test_signup_rejects_duplicate_email(db):
    service = AuthService(db)
    service.sign_up(email="dup@example.com", phone_number=None, password="Password123", full_name="A", role="customer")
    with pytest.raises(ConflictError):
        service.sign_up(email="dup@example.com", phone_number=None, password="Password123", full_name="B", role="customer")


def test_login_with_wrong_password_fails(db):
    service = AuthService(db)
    service.sign_up(email="user@example.com", phone_number=None, password="Password123", full_name="A", role="customer")
    with pytest.raises(UnauthorizedError):
        service.log_in(email="user@example.com", password="WrongPassword1", user_agent=None, ip_address=None)


def test_login_succeeds_with_correct_credentials(db):
    service = AuthService(db)
    service.sign_up(email="user2@example.com", phone_number=None, password="Password123", full_name="A", role="customer")
    result = service.log_in(email="user2@example.com", password="Password123", user_agent=None, ip_address=None)
    assert "access_token" in result and "refresh_token" in result



def test_public_signup_cannot_create_admin():
    from unittest.mock import MagicMock
    from app.core.exceptions import ValidationAppError
    service = AuthService(MagicMock())
    with pytest.raises(ValidationAppError):
        service.sign_up(email="admin@example.com", phone_number=None,
                        password="Password123", full_name="Public Admin", role="admin")
    service.db.add.assert_not_called()
