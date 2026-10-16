"""Password compatibility and long-password regression tests."""
from app.core.security import hash_password, verify_password, pwd_context


def test_long_password_is_not_truncated():
    password = "Password123" + "a" * 100
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password(password[:-1] + "b", hashed)


def test_unicode_password_round_trip():
    password = "密碼" * 30 + "123"
    assert verify_password(password, hash_password(password))


def test_legacy_bcrypt_hash_can_still_be_verified():
    password = "ExistingPassword123"
    legacy = pwd_context.hash(password, scheme="bcrypt")
    assert verify_password(password, legacy)
    assert not verify_password("IncorrectPassword123", legacy)
