"""API-level tests for /api/v1/auth using FastAPI's TestClient."""
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skip(reason="Requires a configured test database via TEST_DATABASE_URL; wire up an app fixture overriding get_db.")


def test_signup_and_login_flow():
    pass
