"""Real database regressions for discovery, onboarding, reset and feedback ownership."""
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ValidationAppError, NotFoundError
from app.core.security import create_password_reset_token, verify_password
from app.models.professional import Professional
from app.models.ai_conversation import AIConversation
from app.models.ai_message import AIMessage
from app.services.auth_service import AuthService
from app.services.ai_navigation_service import AINavigationService


def test_profile_onboarding_search_and_verification(db, make_user):
    tailor = make_user(role='tailor')
    admin = make_user(role='admin')
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: tailor
    try:
        with TestClient(app) as client:
            assert client.get('/api/v1/professionals/me').json() is None
            response = client.put('/api/v1/professionals/me', json={'business_name': 'Lagos Atelier', 'bio': 'Wedding dresses'})
            assert response.status_code == 200, response.text
            profile_id = response.json()['id']
            assert not response.json()['is_verified']
            assert client.get('/api/v1/professionals').json()['total'] == 0
            assert client.post(f'/api/v1/professionals/{profile_id}/verify').status_code == 403
            assert client.put('/api/v1/professionals/me', json={'business_name': 'Lagos Atelier', 'is_verified': True}).status_code == 422
            app.dependency_overrides[get_current_user] = lambda: admin
            assert client.post(f'/api/v1/professionals/{profile_id}/verify').status_code == 200
            results = client.get('/api/v1/professionals?q=Wedding&professional_type=tailor').json()
            assert results['total'] == 1 and results['items'][0]['id'] == profile_id
            assert results['page'] == 1 and results['page_size'] == 20
            assert client.get('/api/v1/professionals?q=unmatched').json()['total'] == 0
            assert client.get('/api/v1/professionals?lat=6').status_code == 422
            assert client.get('/api/v1/professionals?lat=100&lng=3').status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_password_reset_is_single_use_and_revokes_refresh(db, make_user):
    user = make_user()
    service = AuthService(db)
    login = service.log_in(email=user.email, password='Password123', user_agent=None, ip_address=None)
    token = create_password_reset_token(str(user.id), user.hashed_password)
    service.reset_password(token=token, new_password='NewPassword123')
    assert verify_password('NewPassword123', user.hashed_password)
    with pytest.raises(ValidationAppError):
        service.reset_password(token=token, new_password='ReplayPassword123')
    from app.core.exceptions import UnauthorizedError
    with pytest.raises(UnauthorizedError):
        service.refresh_access_token(login['refresh_token'])


def test_feedback_rejects_other_users_message(db, make_user):
    owner, stranger = make_user(), make_user()
    conversation = AIConversation(user_id=owner.id)
    db.add(conversation); db.flush()
    message = AIMessage(conversation_id=conversation.id, role='assistant', content='Hello')
    db.add(message); db.commit()
    with pytest.raises(NotFoundError):
        AINavigationService(db).record_feedback(message.id, user_id=stranger.id, was_helpful=True)
