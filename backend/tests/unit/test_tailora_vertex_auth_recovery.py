"""Vertex authentication recovery must never leak or fabricate credentials."""
import json
from unittest.mock import patch

import pytest

from app.services.vertex_service import VertexAIService, VertexUnavailable


def test_bad_service_account_falls_back_to_express_key():
    fake_client = object()
    with patch("app.services.vertex_service.settings") as settings:
        settings.VERTEX_AI_ENABLED = True
        settings.GCP_PROJECT_ID = "project"
        settings.GCP_SERVICE_ACCOUNT_JSON = "{malformed json"
        settings.GEMINI_API_KEY = None
        settings.VERTEX_AI_API_KEY = "test-express-key"
        settings.GCP_REGION = "us-central1"
        from google import genai
        with patch.object(genai, "Client", return_value=fake_client) as factory:
            result = VertexAIService()._client()
        assert result is fake_client
        factory.assert_called_once_with(vertexai=True, api_key="test-express-key")


def test_bad_service_account_without_fallback_fails_closed():
    with patch("app.services.vertex_service.settings") as settings:
        settings.VERTEX_AI_ENABLED = True
        settings.GCP_PROJECT_ID = "project"
        settings.GCP_SERVICE_ACCOUNT_JSON = "{malformed json"
        settings.GEMINI_API_KEY = None
        settings.VERTEX_AI_API_KEY = None
        with pytest.raises(VertexUnavailable, match="service account"):
            VertexAIService()._client()
