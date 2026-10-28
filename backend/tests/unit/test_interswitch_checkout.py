"""No real Interswitch calls: financial safety and form contract regression tests."""
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from app.core.exceptions import ExternalProviderError
from app.integrations.payments.interswitch_checkout import (
    SANDBOX_CHECKOUT, SANDBOX_REQUERY, build_checkout_form, requery_transaction,
)


def test_checkout_is_post_form_with_minor_units_and_ngn_code():
    checkout = build_checkout_form(
        merchant_code="MX_TEST", pay_item_id="ITEM_TEST", reference="order_123",
        amount="250.50", customer_email="buyer@example.com",
        return_url="https://example.com/payment-result",
    )
    assert checkout.action_url == SANDBOX_CHECKOUT
    assert checkout.fields["amount"] == "25050"
    assert checkout.fields["currency"] == "566"
    assert checkout.fields["payment_response_type"] == "GET"
    assert checkout.fields["txn_ref"] == "order_123"


@pytest.mark.parametrize("reference", ["", "../bad", "bad?ref", "é"])
def test_rejects_unsafe_reference(reference):
    with pytest.raises(ValueError):
        build_checkout_form(
            merchant_code="MX", pay_item_id="123", reference=reference,
            amount="10.00", customer_email="buyer@example.com",
            return_url="https://example.com/return",
        )


@pytest.mark.parametrize("amount", ["0", "-1", "1.001", "NaN"])
def test_rejects_invalid_amount(amount):
    with pytest.raises(ValueError):
        build_checkout_form(
            merchant_code="MX", pay_item_id="123", reference="safe_ref",
            amount=amount, customer_email="buyer@example.com",
            return_url="https://example.com/return",
        )


@pytest.mark.parametrize("url", ["http://example.com/return", "https://evil:pass@example.com/return", "/relative"])
def test_rejects_untrusted_return_url_shape(url):
    with pytest.raises(ValueError):
        build_checkout_form(
            merchant_code="MX", pay_item_id="123", reference="safe_ref",
            amount="10.00", customer_email="buyer@example.com", return_url=url,
        )


def test_requery_accepts_only_authoritative_matching_success():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "MerchantReference": "order_123", "Amount": 25050, "ResponseCode": "00",
    }
    client = SimpleNamespace(get=Mock(return_value=response))
    result = requery_transaction(
        merchant_code="MX_TEST", reference="order_123", expected_amount="250.50",
        client=client,
    )
    assert result.successful is True
    assert result.currency == "NGN"
    args, kwargs = client.get.call_args
    assert args == (SANDBOX_REQUERY,)
    assert kwargs["params"]["amount"] == 25050


@pytest.mark.parametrize("payload", [
    {"MerchantReference": "other", "Amount": 25050, "ResponseCode": "00"},
    {"MerchantReference": "order_123", "Amount": 25049, "ResponseCode": "00"},
    {"MerchantReference": "order_123", "Amount": "25050", "ResponseCode": "00"},
    {"ResponseCode": "00"},
])
def test_requery_fails_closed_on_reference_or_amount_mismatch(payload):
    response = Mock()
    response.json.return_value = payload
    client = SimpleNamespace(get=Mock(return_value=response))
    with pytest.raises(ExternalProviderError, match="mismatch"):
        requery_transaction(merchant_code="MX", reference="order_123",
                            expected_amount="250.50", client=client)


def test_non_success_response_is_not_paid():
    response = Mock()
    response.json.return_value = {
        "MerchantReference": "order_123", "Amount": 25050, "ResponseCode": "Z1",
    }
    result = requery_transaction(
        merchant_code="MX", reference="order_123", expected_amount="250.50",
        client=SimpleNamespace(get=Mock(return_value=response)),
    )
    assert result.successful is False


def test_http_errors_do_not_leak_provider_details():
    client = SimpleNamespace(get=Mock(side_effect=httpx.ConnectError("private provider detail")))
    with pytest.raises(ExternalProviderError) as error:
        requery_transaction(merchant_code="MX", reference="order_123",
                            expected_amount="250.50", client=client)
    assert "private provider detail" not in str(error.value)
