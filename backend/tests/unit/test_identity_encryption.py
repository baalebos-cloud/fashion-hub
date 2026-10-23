from cryptography.fernet import Fernet
import pytest
from app.core.config import settings
from app.core.identity_encryption import encrypt_identity
from app.core.exceptions import ExternalProviderError


def test_identity_requires_dedicated_key(monkeypatch):
    monkeypatch.setattr(settings, 'IDENTITY_ENCRYPTION_KEY', None)
    with pytest.raises(ExternalProviderError):
        encrypt_identity('12345678901')


def test_identity_ciphertext_roundtrips_without_plaintext(monkeypatch):
    key = Fernet.generate_key()
    monkeypatch.setattr(settings, 'IDENTITY_ENCRYPTION_KEY', key.decode())
    encrypted = encrypt_identity('12345678901')
    assert encrypted.startswith('fernet:v1:')
    assert '12345678901' not in encrypted
    assert Fernet(key).decrypt(encrypted.removeprefix('fernet:v1:').encode()) == b'12345678901'
