"""HTTP regressions for security and operational contracts (no live DB calls)."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app


@pytest.fixture()
def client():
    def fake_db():
        yield MagicMock()
    app.dependency_overrides[get_db] = fake_db
    with TestClient(app) as http:
        yield http
    app.dependency_overrides.clear()


def test_public_signup_rejects_admin(client):
    response = client.post('/api/v1/auth/signup', json={
        'email': 'attacker@example.com', 'password': 'Password123',
        'full_name': 'Public User', 'role': 'admin',
    })
    assert response.status_code == 422


def test_readiness_returns_503_when_database_unavailable(client, monkeypatch):
    monkeypatch.setattr('app.main.check_database_health', lambda: False)
    monkeypatch.setattr('app.main.check_redis_health', lambda: True)
    response = client.get('/health/ready')
    assert response.status_code == 503
    assert response.json()['checks']['database'] is False
    assert client.get('/health/live').status_code == 200


def test_readiness_returns_200_when_dependencies_available(client, monkeypatch):
    monkeypatch.setattr('app.main.check_database_health', lambda: True)
    monkeypatch.setattr('app.main.check_redis_health', lambda: True)
    assert client.get('/health/ready').status_code == 200


def test_cors_rejects_unapproved_origin(client):
    response = client.options('/api/v1/users/me', headers={
        'Origin': 'https://attacker.example', 'Access-Control-Request-Method': 'GET',
    })
    assert response.status_code == 400
    assert 'access-control-allow-origin' not in response.headers


def test_cors_accepts_configured_local_origin(client):
    response = client.options('/api/v1/users/me', headers={
        'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'authorization',
    })
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'


def test_unsigned_payment_delivery_fails_closed(client, monkeypatch):
    monkeypatch.setattr('app.core.config.settings.PAYMENT_SECRET_KEY', None)
    from app.integrations.payments import get_payment_provider
    get_payment_provider.cache_clear()
    response = client.post('/api/v1/payments/webhooks/paystack', content=b'{bad json')
    assert response.status_code == 401
    get_payment_provider.cache_clear()


def test_request_id_is_bounded(client):
    response = client.get('/health/live', headers={'X-Request-ID': 'x' * 1000})
    assert len(response.headers['X-Request-ID']) <= 64
    assert response.headers['X-Content-Type-Options'] == 'nosniff'


def test_login_rate_limit_is_enforced(client, monkeypatch):
    from app.core.rate_limit import limiter
    limiter.reset()
    monkeypatch.setattr('app.services.auth_service.AuthService.log_in', lambda *a, **k: {
        'access_token': 'test-access', 'refresh_token': 'test-refresh',
    })
    try:
        for _ in range(10):
            response = client.post('/api/v1/auth/login', json={
                'email': 'rate-test@example.com', 'password': 'Password123',
            })
            assert response.status_code == 200
        response = client.post('/api/v1/auth/login', json={
            'email': 'rate-test@example.com', 'password': 'Password123',
        })
        assert response.status_code == 429
    finally:
        limiter.reset()
