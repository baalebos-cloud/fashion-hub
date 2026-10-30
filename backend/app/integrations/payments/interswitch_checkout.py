"""Opt-in Interswitch Nigeria Web Redirect primitives.

Not wired into PaymentProvider: Web Redirect requires a browser POST form,
whereas PaymentProvider.initialize_payment currently promises a GET redirect.
Only a separately reviewed orchestration change may enable settlement.
Docs: https://docs.interswitchgroup.com/docs/web-checkout
"""
from dataclasses import dataclass
import logging
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

from app.core.exceptions import ExternalProviderError
from app.core.policies import money_to_minor_units

SANDBOX_CHECKOUT = "https://newwebpay-sandbox.interswitchng.com/collections/w/pay"
SANDBOX_REQUERY = "https://sandbox.interswitchng.com/collections/api/v1/gettransaction.json"
LIVE_CHECKOUT = "https://newwebpay.interswitchng.com/collections/w/pay"
LIVE_REQUERY = "https://webpay.interswitchng.com/collections/api/v1/gettransaction.json"


@dataclass(frozen=True)
class CheckoutForm:
    action_url: str
    fields: dict[str, str]


@dataclass(frozen=True)
class RequeryResult:
    reference: str
    amount_minor: int
    currency: str
    successful: bool


def build_checkout_form(*, merchant_code: str, pay_item_id: str, reference: str,
                        amount, customer_email: str, return_url: str,
                        live: bool = False) -> CheckoutForm:
    """Build a POST form; nothing is charged and no payment is confirmed."""
    if not all(isinstance(value, str) and value.strip() for value in (
        merchant_code, pay_item_id, reference, customer_email, return_url
    )):
        raise ValueError("All checkout identifiers and return URL are required")
    if len(reference) > 128 or not reference.isascii() or not all(
        char.isalnum() or char in "-_" for char in reference
    ):
        raise ValueError("Transaction reference must be a safe unique identifier")
    target = urlparse(return_url)
    if target.scheme != "https" or not target.netloc or target.username or target.password or target.fragment:
        raise ValueError("Return URL must be an absolute HTTPS URL")
    return CheckoutForm(
        action_url=LIVE_CHECKOUT if live else SANDBOX_CHECKOUT,
        fields={
            "merchant_code": merchant_code,
            "pay_item_id": pay_item_id,
            "txn_ref": reference,
            "amount": str(money_to_minor_units(amount)),
            "currency": "566",
            "cust_email": customer_email,
            "site_redirect_url": return_url,
            "payment_response_type": "GET",
        },
    )


def requery_transaction(*, merchant_code: str, reference: str, expected_amount,
                        live: bool = False, client=None) -> RequeryResult:
    """Verify against Interswitch independently; fail closed on any mismatch.

    The endpoint returns Amount in NGN minor units and MerchantReference.
    Currency is NGN-only in this isolated adapter (ISO numeric 566).
    """
    if not merchant_code or not reference:
        raise ValueError("Missing merchant code or transaction reference")
    expected_minor = money_to_minor_units(expected_amount)
    url = LIVE_REQUERY if live else SANDBOX_REQUERY
    requester = client or httpx
    try:
        response = requester.get(url, params={
            "merchantcode": merchant_code,
            "transactionreference": reference,
            "amount": expected_minor,
        }, timeout=15.0)
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.warning("interswitch_requery_timeout environment=%s", "live" if live else "sandbox")
        raise ExternalProviderError("Interswitch verification timed out. Try checking again.") from exc
    except httpx.HTTPStatusError as exc:
        logger.warning("interswitch_requery_http_error environment=%s status=%s",
                       "live" if live else "sandbox", exc.response.status_code)
        raise ExternalProviderError("Interswitch verification service rejected the request.") from exc
    except httpx.RequestError as exc:
        logger.warning("interswitch_requery_transport_error environment=%s type=%s",
                       "live" if live else "sandbox", type(exc).__name__)
        raise ExternalProviderError("Interswitch verification service is unreachable.") from exc
    try:
        data = response.json()
    except (ValueError, TypeError) as exc:
        logger.warning("interswitch_requery_invalid_json environment=%s", "live" if live else "sandbox")
        raise ExternalProviderError("Interswitch verification returned an invalid response.") from exc
    if not isinstance(data, dict):
        logger.warning("interswitch_requery_invalid_shape environment=%s", "live" if live else "sandbox")
        raise ExternalProviderError("Interswitch verification returned an invalid response.")
    received_reference = data.get("MerchantReference")
    amount = data.get("Amount")
    if (received_reference != reference or isinstance(amount, bool)
            or not isinstance(amount, int) or amount != expected_minor):
        logger.warning("interswitch_requery_mismatch environment=%s reference_matches=%s amount_matches=%s",
                       "live" if live else "sandbox", received_reference == reference,
                       isinstance(amount, int) and not isinstance(amount, bool) and amount == expected_minor)
        raise ExternalProviderError("Interswitch verification details do not match the order.")
    logger.info("interswitch_requery_result environment=%s approved=%s",
                "live" if live else "sandbox", data.get("ResponseCode") == "00")
    # A callback, HTTP 200, or non-00 code never establishes a paid order.
    return RequeryResult(
        reference=reference, amount_minor=amount, currency="NGN",
        successful=data.get("ResponseCode") == "00",
    )
