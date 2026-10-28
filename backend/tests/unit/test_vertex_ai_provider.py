"""Offline Vertex AI express-mode transport and Seam fallback tests."""
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from app.core.config import settings
from app.core.exceptions import ExternalProviderError
from app.integrations.ai.llm_client import ChatMessage, LLMClient
from app.integrations.ai.navigation_agent import build_navigation_response


@pytest.fixture(autouse=True)
def configure_vertex(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "vertex_ai")
    monkeypatch.setattr(settings, "VERTEX_AI_API_KEY", "test-express-key")
    monkeypatch.setattr(settings, "AI_MODEL", "gemini-3-flash-preview")


def test_vertex_endpoint_key_and_role_prompt(monkeypatch):
    sender = Mock(return_value=SimpleNamespace(
        status_code=200,
        json=lambda: {"candidates": [{"content": {"parts": [{"text": "Open Orders and accept."}]}}]},
    ))
    monkeypatch.setattr(httpx, "post", sender)
    answer = build_navigation_response(
        user_role="tailor", user_question="How do I accept an order?"
    )
    assert answer == "Open Orders and accept."
    sender.assert_called_once()
    args, kwargs = sender.call_args
    assert args == (
        "https://aiplatform.googleapis.com/v1/publishers/google/models/gemini-3-flash-preview:generateContent",
    )
    assert kwargs["headers"]["x-goog-api-key"] == "test-express-key"
    assert kwargs["timeout"] == 20.0
    assert "Incoming Orders" in kwargs["json"]["systemInstruction"]["parts"][0]["text"]
    assert "/app/admin" not in str(kwargs["json"])
    assert kwargs["json"]["contents"] == [
        {"role": "user", "parts": [{"text": "How do I accept an order?"}]}
    ]


def test_vertex_converts_assistant_turns_to_model_role(monkeypatch):
    sender = Mock(return_value=SimpleNamespace(
        status_code=200,
        json=lambda: {"candidates": [{"content": {"parts": [
            {"text": "First"}, {"text": " response"},
        ]}}]},
    ))
    monkeypatch.setattr(httpx, "post", sender)
    result = LLMClient().complete([
        ChatMessage("system", "Only help with navigation"),
        ChatMessage("user", "Hello"),
        ChatMessage("assistant", "Hi"),
        ChatMessage("user", "Where are orders?"),
    ], max_tokens=128)
    assert result.content == "First response"
    payload = sender.call_args.kwargs["json"]
    assert [turn["role"] for turn in payload["contents"]] == ["user", "model", "user"]
    assert payload["generationConfig"]["maxOutputTokens"] == 1024
    assert payload["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "LOW"}


def test_vertex_missing_credentials_and_invalid_model_fail_closed(monkeypatch):
    monkeypatch.setattr(settings, "VERTEX_AI_API_KEY", None)
    with pytest.raises(ExternalProviderError, match="credentials"):
        LLMClient().complete([ChatMessage("user", "Hi")])
    monkeypatch.setattr(settings, "VERTEX_AI_API_KEY", "test-express-key")
    with pytest.raises(ExternalProviderError, match="Gemini model"):
        LLMClient(model="../external-host").complete([ChatMessage("user", "Hi")])


def test_vertex_provider_failures_do_not_expose_secrets_or_response(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: SimpleNamespace(
        status_code=403, text="PRIVATE-API-RESPONSE"
    ))
    with pytest.raises(ExternalProviderError) as error:
        LLMClient().complete([ChatMessage("user", "Hello")])
    assert "403" in str(error.value)
    assert "PRIVATE-API-RESPONSE" not in str(error.value)
    assert settings.VERTEX_AI_API_KEY not in str(error.value)

    def connection_error(*args, **kwargs):
        raise httpx.ConnectError("PRIVATE-NETWORK-ADDRESS",
                                 request=httpx.Request("POST", args[0]))
    monkeypatch.setattr(httpx, "post", connection_error)
    with pytest.raises(ExternalProviderError, match="unreachable") as error:
        LLMClient().complete([ChatMessage("user", "Hello")])
    assert "PRIVATE-NETWORK-ADDRESS" not in str(error.value)


def test_seam_navigation_fallback_if_old_n8n_config_or_google_outage(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "n8n")
    for role, route in [
        ("tailor", "/app/professional/orders"),
        ("vendor", "/app/vendor/orders"),
        ("customer", "/app/customer/orders"),
    ]:
        answer = build_navigation_response(
            user_role=role, user_question="How do I accept an order?"
        )
        assert route in answer
        assert "Unsupported AI_PROVIDER" not in answer
        assert "temporarily unavailable" in answer
    other = build_navigation_response(
        user_role="customer", user_question="Where are admin tools?"
    )
    assert "/app/admin" not in other


def test_vertex_rejection_diagnostics_are_safe(monkeypatch):
    from app.integrations.ai import llm_client
    warning = Mock()
    monkeypatch.setattr(llm_client.logger, "warning", warning)
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: SimpleNamespace(
        status_code=403,
        json=lambda: {"error": {"status": "PERMISSION_DENIED", "message": "Provider diagnostic detail"}},
    ))
    with pytest.raises(ExternalProviderError, match="403"):
        LLMClient().complete([ChatMessage("user", "How do I accept an order?")])
    warning.assert_called_once()
    assert warning.call_args.args[0] == "seam_vertex_api_failure"
    assert warning.call_args.kwargs["extra"] == {
        "provider": "vertex_ai", "http_status": 403,
        "provider_code": "PERMISSION_DENIED",
    }


def test_empty_gemini_response_logs_safe_finish_reason(monkeypatch):
    from app.integrations.ai import llm_client
    warning = Mock()
    monkeypatch.setattr(llm_client.logger, "warning", warning)
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: SimpleNamespace(
        status_code=200, json=lambda: {"candidates": [{
            "finishReason": "MAX_TOKENS",
            "content": {"parts": [{"thought": True, "text": "internal model text"}]},
        }]},
    ))
    with pytest.raises(ExternalProviderError, match="did not return an answer"):
        LLMClient().complete([ChatMessage("user", "Where are my orders?")])
    warning.assert_called_once()
    assert warning.call_args.args[0] == "seam_vertex_empty_response"
    assert warning.call_args.kwargs["extra"] == {
        "provider": "vertex_ai", "finish_reason": "MAX_TOKENS",
    }


def test_capabilities_fallback_is_role_scoped(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "n8n")
    response = build_navigation_response(
        user_role="tailor", user_question="What can you do as an AI assistant?"
    )
    assert "incoming orders" in response
    assert "materials" in response
    assert "do not accept orders" in response
    assert "/app/admin" not in response
