"""Resend transport regressions: no external requests or real provider keys."""
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from app.core.config import settings
from app.core.exceptions import ExternalProviderError
from app.integrations.notifications.email import send_email


@pytest.fixture(autouse=True)
def configured_resend(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(settings, "EMAIL_API_KEY", "fake-resend-token-for-tests")
    monkeypatch.setattr(settings, "EMAIL_FROM_ADDRESS", "Fashion Hub <mail@fashion.test>")


def test_resend_email_uses_https_and_stable_idempotency_key(monkeypatch):
    sender = Mock(return_value=SimpleNamespace(status_code=200))
    monkeypatch.setattr(httpx, "post", sender)
    send_email(to_address="buyer@example.com", subject="Verify", html_body="<p>Link</p>",
               idempotency_key="auth-email-123")
    sender.assert_called_once()
    args, kwargs = sender.call_args
    assert args == ("https://api.resend.com/emails",)
    assert kwargs["json"] == {"from": settings.EMAIL_FROM_ADDRESS,
                              "to": ["buyer@example.com"], "subject": "Verify", "html": "<p>Link</p>"}
    assert kwargs["headers"]["Idempotency-Key"] == "auth-email-123"
    assert kwargs["headers"]["Authorization"] == "Bearer fake-resend-token-for-tests"
    assert kwargs["timeout"] > 0


def test_missing_key_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_API_KEY", None)
    with pytest.raises(ExternalProviderError, match="API key"):
        send_email(to_address="buyer@example.com", subject="Verify", html_body="<p>x</p>")


def test_provider_errors_do_not_leak_response_content_or_key(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: SimpleNamespace(
        status_code=403, text="SECRET-TOKEN"));
    with pytest.raises(ExternalProviderError) as error:
        send_email(to_address="buyer@example.com", subject="Verify", html_body="<p>x</p>")
    assert "403" in str(error.value)
    assert "SECRET-TOKEN" not in str(error.value)
    assert settings.EMAIL_API_KEY not in str(error.value)


def test_transport_errors_are_retryable_provider_failures(monkeypatch):
    def unavailable(*args, **kwargs):
        raise httpx.ConnectError("private URL", request=httpx.Request("POST", "https://api.resend.com/emails"))
    monkeypatch.setattr(httpx, "post", unavailable)
    with pytest.raises(ExternalProviderError, match="unreachable") as error:
        send_email(to_address="buyer@example.com", subject="Verify", html_body="<p>x</p>")
    assert "private URL" not in str(error.value)
