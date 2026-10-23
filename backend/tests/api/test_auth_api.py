"""Real HTTP authentication and legacy-credential migration on disposable data."""
import pytest
from fastapi.testclient import TestClient
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import create_access_token, create_refresh_token, pwd_context
from app.main import app
from app.models.user import User


@pytest.fixture()
def client(db, monkeypatch):
    def override_db():
        yield db
    app.dependency_overrides[get_db] = override_db
    limiter.reset()
    monkeypatch.setattr('app.workers.email_tasks.send_verification_email_task.delay', lambda **kwargs: None)
    try:
        with TestClient(app) as http:
            yield http
    finally:
        app.dependency_overrides.clear()
        limiter.reset()


def test_signup_and_login_flow(client, db):
    password = 'NewAccountPassword123'
    response = client.post('/api/v1/auth/signup', json={'email': 'http-signup@example.com', 'password': password,
                           'full_name': 'HTTP Customer', 'role': 'customer'})
    assert response.status_code == 201, response.text
    user = db.query(User).filter(User.email == 'http-signup@example.com').one()
    assert user.hashed_password.startswith('$argon2id$')
    login = client.post('/api/v1/auth/login', json={'email': user.email, 'password': password})
    assert login.status_code == 200, login.text
    tokens = login.json()
    assert client.get('/api/v1/orders', headers={'Authorization': 'Bearer ' + tokens['access_token']}).status_code == 200
    refreshed = client.post('/api/v1/auth/refresh', json={'refresh_token': tokens['refresh_token']})
    assert refreshed.status_code == 200, refreshed.text
    assert client.get('/api/v1/orders', headers={'Authorization': 'Bearer ' + refreshed.json()['access_token']}).status_code == 200
    assert refreshed.json()['refresh_token'] != tokens['refresh_token']
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': tokens['refresh_token']}).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': refreshed.json()['refresh_token']}).status_code == 200


def test_vendor_signup_login_and_authenticated_identity(client, db):
    password = 'NewVendorPassword123'
    response = client.post('/api/v1/auth/signup', json={
        'email': 'http-vendor@example.com', 'password': password,
        'full_name': 'HTTP Vendor', 'role': 'vendor',
    })
    assert response.status_code == 201, response.text
    assert response.json()['role'] == 'vendor'
    user = db.query(User).filter(User.email == 'http-vendor@example.com').one()
    assert user.role == 'vendor' and user.hashed_password.startswith('$argon2id$')

    login = client.post('/api/v1/auth/login', json={'email': user.email, 'password': password})
    assert login.status_code == 200, login.text
    identity = client.get('/api/v1/users/me', headers={
        'Authorization': 'Bearer ' + login.json()['access_token'],
    })
    assert identity.status_code == 200, identity.text
    assert identity.json()['role'] == 'vendor' and identity.json()['email'] == user.email


@pytest.mark.parametrize('scheme', ['bcrypt', 'bcrypt_sha256'])
def test_legacy_login_upgrades_through_http(client, db, make_user, scheme):
    password = 'LegacyPassword123'
    user = make_user(hashed_password=pwd_context.hash(password, scheme=scheme))
    response = client.post('/api/v1/auth/login', json={'email': user.email, 'password': password})
    assert response.status_code == 200, response.text
    db.refresh(user)
    assert user.hashed_password.startswith('$argon2id$')
    assert client.get('/api/v1/orders', headers={'Authorization': 'Bearer ' + response.json()['access_token']}).status_code == 200


def test_refresh_and_tampered_tokens_cannot_access_protected_http_routes(client, make_user):
    user = make_user()
    access = create_access_token(str(user.id), user.role)
    tokens = [create_refresh_token(str(user.id)), access.rsplit('.', 1)[0] + '.invalid']
    for token in tokens:
        assert client.get('/api/v1/orders', headers={'Authorization': 'Bearer ' + token}).status_code == 401


def test_inactive_user_cannot_use_an_existing_token(client, db, make_user):
    user = make_user()
    token = create_access_token(str(user.id), user.role)
    user.is_active = False
    db.commit()
    assert client.get('/api/v1/orders', headers={'Authorization': 'Bearer ' + token}).status_code == 401


def test_auth_emails_are_durable_encrypted_and_sent_once(db, make_user, monkeypatch):
    from unittest.mock import patch
    from app.models.notification import Notification
    from app.services.auth_service import AuthService
    from app.services.auth_email_outbox_service import AuthEmailOutboxService

    # No external email provider or Celery broker is required for this test.
    monkeypatch.setattr("app.services.auth_service.settings.APP_ENV", "test")
    user = make_user()
    service = AuthService(db)
    service.request_password_reset(user.email)
    job = db.query(Notification).filter_by(recipient_user_id=user.id, event_type="auth.password_reset").one()
    assert job.metadata_json["ciphertext"].startswith("gAAAA")
    assert user.email not in str(job.metadata_json)
    with patch("app.integrations.notifications.email.send_email") as sender:
        assert AuthEmailOutboxService(db).process_one()
        sender.assert_called_once()
        assert "/reset-password?token=" in sender.call_args.kwargs["html_body"]
        assert not AuthEmailOutboxService(db).process_one()
    db.refresh(job)
    assert job.sent_at and job.metadata_json is None
