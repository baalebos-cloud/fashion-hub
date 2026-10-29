"""Prembly NIN Basic contract tests; no external network or actual NIN used."""
from datetime import date
from unittest.mock import patch, Mock
import pytest
from app.integrations.kyc.prembly import PremblyNINProvider, PREMBLY_BASE_URL
from app.core.exceptions import ExternalProviderError, NotFoundError


def test_current_nin_basic_contract():
    response = Mock()
    response.json.return_value = {
        "status": True, "response_code": "00",
        "data": {"firstname": "TEST", "middlename": "", "surname": "PERSON",
                 "birthdate": "23-05-1999", "gender": "f"},
    }
    with patch("app.integrations.kyc.prembly.httpx.post", return_value=response) as post:
        result = PremblyNINProvider(api_key="test-only-key").verify("12345678901")
    assert result.full_name.replace("  ", " ") == "TEST PERSON"
    assert result.date_of_birth == date(1999, 5, 23)
    assert result.gender == "F"
    assert post.call_args.args[0] == PREMBLY_BASE_URL
    assert post.call_args.kwargs["json"] == {"number": "12345678901"}
    assert post.call_args.kwargs["headers"]["x-api-key"] == "test-only-key"
    assert "app-id" not in post.call_args.kwargs["headers"]


def test_incomplete_identity_is_never_accepted():
    response = Mock()
    response.json.return_value = {"status": True, "response_code": "00", "data": {}}
    with patch("app.integrations.kyc.prembly.httpx.post", return_value=response):
        with pytest.raises(ExternalProviderError):
            PremblyNINProvider(api_key="test-only-key").verify("12345678901")


def test_missing_credentials_fail_closed(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "NIN_API_KEY", None)
    with pytest.raises(ExternalProviderError):
        PremblyNINProvider().verify("12345678901")
