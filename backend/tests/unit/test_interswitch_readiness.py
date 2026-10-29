"""Interswitch preflight is read-only and never exposes merchant IDs or credentials."""
from app.core.config import settings
from app.services.interswitch_readiness import sandbox_readiness


def test_sandbox_readiness_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "staging")
    monkeypatch.setattr(settings, "APP_URL", "https://staging.example.test")
    monkeypatch.setattr(settings, "INTERSWITCH_SANDBOX_ENABLED", True)
    monkeypatch.setattr(settings, "INTERSWITCH_MERCHANT_CODE", "secret-test-merchant")
    monkeypatch.setattr(settings, "INTERSWITCH_PAY_ITEM_ID", "secret-test-payitem")
    result = sandbox_readiness()
    assert result["ready"] is True
    assert result["mode"] == "sandbox"
    assert "secret-test" not in str(result)


def test_sandbox_preflight_fails_closed_in_production(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "APP_URL", "https://api.example.test")
    monkeypatch.setattr(settings, "INTERSWITCH_SANDBOX_ENABLED", True)
    monkeypatch.setattr(settings, "INTERSWITCH_MERCHANT_CODE", "merchant")
    monkeypatch.setattr(settings, "INTERSWITCH_PAY_ITEM_ID", "payitem")
    result = sandbox_readiness()
    assert result["ready"] is False
    assert result["checks"]["non_production_environment"] is False


def test_sandbox_preflight_rejects_http_callback(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "staging")
    monkeypatch.setattr(settings, "APP_URL", "http://localhost:8000")
    monkeypatch.setattr(settings, "INTERSWITCH_SANDBOX_ENABLED", True)
    monkeypatch.setattr(settings, "INTERSWITCH_MERCHANT_CODE", "merchant")
    monkeypatch.setattr(settings, "INTERSWITCH_PAY_ITEM_ID", "payitem")
    assert sandbox_readiness()["checks"]["https_callback"] is False
