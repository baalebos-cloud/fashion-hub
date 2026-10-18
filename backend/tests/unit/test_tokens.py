"""JWT migration compatibility, signature/claim validation and type isolation."""
from datetime import datetime, timedelta, timezone
import uuid
import jwt
import pytest
from app.core.config import settings
from app.core.security import JWTError, create_access_token, create_refresh_token, decode_token


def claims(**overrides):
    return {'sub': str(uuid.uuid4()), 'iat': datetime.now(timezone.utc),
            'exp': datetime.now(timezone.utc) + timedelta(minutes=5),
            'type': 'access', 'jti': str(uuid.uuid4()), 'role': 'customer', **overrides}


def test_token_round_trip_and_refresh_cannot_be_used_as_access():
    subject = str(uuid.uuid4())
    payload = decode_token(create_access_token(subject, 'customer'), expected_type='access')
    assert payload['sub'] == subject and payload['role'] == 'customer'
    with pytest.raises(ValueError):
        decode_token(create_refresh_token(subject), expected_type='access')


@pytest.mark.parametrize('mutation', ['expired', 'signature', 'algorithm', 'unsigned', 'missing_exp', 'missing_sub', 'empty_sub'])
def test_invalid_jwt_is_rejected(mutation):
    payload = claims()
    key, algorithm = settings.SECRET_KEY, settings.JWT_ALGORITHM
    if mutation == 'expired': payload['exp'] = datetime.now(timezone.utc) - timedelta(minutes=1)
    if mutation == 'signature': key = 'incorrect-signing-key-that-is-long-enough'
    if mutation == 'algorithm': algorithm = 'HS512' if algorithm != 'HS512' else 'HS256'
    if mutation == 'unsigned': key, algorithm = '', 'none'
    if mutation == 'missing_exp': payload.pop('exp')
    if mutation == 'missing_sub': payload.pop('sub')
    if mutation == 'empty_sub': payload['sub'] = ''
    with pytest.raises(JWTError):
        decode_token(jwt.encode(payload, key, algorithm=algorithm), expected_type='access')


def test_server_identity_role_and_expiry_cannot_be_overwritten_by_extra_claims():
    subject = str(uuid.uuid4())
    token = create_access_token(subject, 'customer', {'sub': 'other', 'role': 'admin', 'exp': 0, 'type': 'refresh', 'tenant': 'test'})
    payload = decode_token(token, expected_type='access')
    assert payload['sub'] == subject and payload['role'] == 'customer' and payload['tenant'] == 'test'
