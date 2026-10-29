"""Offline live checkout safety contracts; no provider calls or money movement."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.core.exceptions import ConflictError
from app.integrations.payments.interswitch_checkout import LIVE_CHECKOUT, LIVE_REQUERY
from app.services.interswitch_live_service import InterswitchLiveService


@pytest.fixture
def disabled(monkeypatch):
    monkeypatch.setattr(settings, "INTERSWITCH_LIVE_ENABLED", False)
    monkeypatch.setattr(settings, "APP_ENV", "staging")
    monkeypatch.setattr(settings, "INTERSWITCH_LIVE_MERCHANT_CODE", None)
    monkeypatch.setattr(settings, "INTERSWITCH_LIVE_PAY_ITEM_ID", None)


def test_live_cannot_run_in_staging_even_if_enabled(disabled, monkeypatch):
    monkeypatch.setattr(settings, "INTERSWITCH_LIVE_ENABLED", True)
    monkeypatch.setattr(settings, "INTERSWITCH_LIVE_MERCHANT_CODE", "MX153376")
    monkeypatch.setattr(settings, "INTERSWITCH_LIVE_PAY_ITEM_ID", "5558761")
    with pytest.raises(ConflictError):
        InterswitchLiveService._require_sandbox()


def test_live_disabled_by_default(disabled, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    with pytest.raises(ConflictError):
        InterswitchLiveService._require_sandbox()


def test_live_requires_assigned_pay_item(disabled, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "INTERSWITCH_LIVE_ENABLED", True)
    monkeypatch.setattr(settings, "INTERSWITCH_LIVE_MERCHANT_CODE", "MX153376")
    with pytest.raises(ConflictError):
        InterswitchLiveService._require_sandbox()


def test_live_form_uses_hosted_gateway_and_minor_units(disabled, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "APP_URL", "https://api.example.test")
    monkeypatch.setattr(settings, "INTERSWITCH_LIVE_MERCHANT_CODE", "MX153376")
    monkeypatch.setattr(settings, "INTERSWITCH_LIVE_PAY_ITEM_ID", "5558761")
    fake_payment = SimpleNamespace(provider_reference="safe_live_123", amount=Decimal("10.00"))
    service = object.__new__(InterswitchLiveService)
    form = service._checkout_form(fake_payment, "buyer@example.test")
    assert form.action_url == LIVE_CHECKOUT
    assert form.fields["amount"] == "1000"
    assert form.fields["merchant_code"] == "MX153376"
    assert form.fields["pay_item_id"] == "5558761"
    assert form.fields["site_redirect_url"].startswith("https://")


def test_live_requery_target_is_distinct_from_sandbox():
    assert LIVE_REQUERY.startswith("https://")
    assert "sandbox" not in LIVE_REQUERY
