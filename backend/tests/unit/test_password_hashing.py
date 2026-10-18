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


def test_new_hashes_use_argon2id_and_do_not_need_an_update():
    from app.core.security import verify_and_update_password
    password = 'NewPassword123'
    hashed = hash_password(password)
    assert hashed.startswith('$argon2id$')
    assert verify_and_update_password(password, hashed) == (True, None)


def test_bcrypt_sha256_remains_compatible_and_upgrades():
    from app.core.security import verify_and_update_password
    password = '密碼Password123' + 'a' * 100
    legacy = pwd_context.hash(password, scheme='bcrypt_sha256')
    valid, updated = verify_and_update_password(password, legacy)
    assert valid and updated.startswith('$argon2id$')
    assert verify_password(password, updated)
    assert not verify_password(password[:-1] + 'b', updated)


def test_wrong_or_invalid_hash_never_requests_an_upgrade():
    from app.core.security import verify_and_update_password
    for hashed in [hash_password('CorrectPassword123'), 'not-a-hash', '$argon2id$malformed']:
        assert verify_and_update_password('WrongPassword123', hashed) == (False, None)
