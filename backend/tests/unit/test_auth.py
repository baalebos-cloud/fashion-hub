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


@pytest.mark.parametrize('scheme', ['bcrypt', 'bcrypt_sha256'])
def test_successful_legacy_login_upgrades_password_and_retains_token_flow(db, make_user, scheme):
    from app.core.security import pwd_context, decode_token, verify_password
    password = 'ExistingPassword123'
    user = make_user(hashed_password=pwd_context.hash(password, scheme=scheme))
    service = AuthService(db)
    result = service.log_in(email=user.email, password=password, user_agent=None, ip_address=None)
    db.refresh(user)
    assert user.hashed_password.startswith('$argon2id$')
    assert verify_password(password, user.hashed_password)
    assert decode_token(result['access_token'], expected_type='access')['sub'] == str(user.id)
    assert decode_token(service.refresh_access_token(result['refresh_token']), expected_type='access')['sub'] == str(user.id)


def test_failed_or_inactive_legacy_login_does_not_replace_hash(db, make_user):
    from app.core.security import pwd_context
    from app.core.exceptions import UnauthorizedError
    legacy = pwd_context.hash('ExistingPassword123', scheme='bcrypt')
    user = make_user(hashed_password=legacy)
    service = AuthService(db)
    with pytest.raises(UnauthorizedError):
        service.log_in(email=user.email, password='WrongPassword123', user_agent=None, ip_address=None)
    db.refresh(user)
    assert user.hashed_password == legacy
    user.is_active = False
    db.commit()
    with pytest.raises(UnauthorizedError):
        service.log_in(email=user.email, password='ExistingPassword123', user_agent=None, ip_address=None)
    db.refresh(user)
    assert user.hashed_password == legacy
