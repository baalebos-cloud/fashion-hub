"""Provider failover: Vertex stays primary, Groq handles provider errors only."""
from unittest.mock import patch, Mock
import httpx
import pytest
from app.integrations.ai.llm_client import LLMClient, ChatMessage
from app.core.exceptions import ExternalProviderError


def test_vertex_primary_success_does_not_use_groq(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "AI_PROVIDER", "vertex_ai")
    monkeypatch.setattr(settings, "AI_FALLBACK_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-secret")
    client = LLMClient()
    with patch.object(client, "_complete_vertex_ai", return_value="vertex-result"), patch.object(client, "_complete_groq") as fallback:
        assert client.complete([ChatMessage(role="user", content="hi")]) == "vertex-result"
        fallback.assert_not_called()


def test_vertex_failure_uses_groq(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "AI_PROVIDER", "vertex_ai")
    monkeypatch.setattr(settings, "AI_FALLBACK_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-secret")
    client = LLMClient()
    with patch.object(client, "_complete_vertex_ai", side_effect=ExternalProviderError("Unavailable")), patch.object(client, "_complete_groq", return_value="groq-result"):
        assert client.complete([ChatMessage(role="user", content="hi")]) == "groq-result"


def test_no_groq_key_keeps_primary_failure(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "AI_PROVIDER", "vertex_ai")
    monkeypatch.setattr(settings, "AI_FALLBACK_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    client = LLMClient()
    with patch.object(client, "_complete_vertex_ai", side_effect=ExternalProviderError("Unavailable")):
        with pytest.raises(ExternalProviderError):
            client.complete([ChatMessage(role="user", content="hi")])


def test_groq_complete_parses_response(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-secret")
    monkeypatch.setattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
    response = Mock(status_code=200)
    response.json.return_value = {"choices": [{"message": {"content": "A tailored suggestion"}}]}
    with patch("app.integrations.ai.llm_client.httpx.post", return_value=response) as post:
        result = LLMClient()._complete_groq([ChatMessage(role="user", content="hello")], 256)
    assert result.content == "A tailored suggestion"
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-secret"
