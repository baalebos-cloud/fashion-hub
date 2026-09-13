"""
Flutterwave implementation of PaymentProvider.
Docs: https://developer.flutterwave.com/docs
"""
import hashlib
import hmac

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError
from app.integrations.payments.base import (
    InitializePaymentResult,
    PaymentProvider,
    VerifyPaymentResult,
)

FLUTTERWAVE_BASE_URL = "https://api.flutterwave.com/v3"


class FlutterwaveProvider(PaymentProvider):
    def __init__(self, secret_key: str | None = None):
        self.secret_key = secret_key or settings.PAYMENT_SECRET_KEY

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.secret_key}", "Content-Type": "application/json"}

    def initialize_payment(
        self, *, order_id: str, amount: float, currency: str, customer_email: str, callback_url: str
    ) -> InitializePaymentResult:
        try:
            response = httpx.post(
                f"{FLUTTERWAVE_BASE_URL}/payments",
                headers=self._headers(),
                json={
                    "tx_ref": order_id,
                    "amount": str(amount),
                    "currency": currency,
                    "redirect_url": callback_url,
                    "customer": {"email": customer_email},
                },
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()["data"]
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"Flutterwave initialize_payment failed: {exc}") from exc

        return InitializePaymentResult(
            provider_reference=order_id, authorization_url=data["link"], raw_response=data
        )

    def verify_payment(self, provider_reference: str) -> VerifyPaymentResult:
        try:
            response = httpx.get(
                f"{FLUTTERWAVE_BASE_URL}/transactions/verify_by_reference",
                headers=self._headers(),
                params={"tx_ref": provider_reference},
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()["data"]
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"Flutterwave verify_payment failed: {exc}") from exc

        status_map = {"successful": "successful", "failed": "failed"}
        return VerifyPaymentResult(
            provider_reference=provider_reference,
            status=status_map.get(data["status"], "pending"),
            amount=data["amount"],
            currency=data["currency"],
            paid_at=data.get("created_at"),
            raw_response=data,
        )

    def verify_webhook_signature(self, *, payload: bytes, signature_header: str) -> bool:
        # Flutterwave uses a static verif-hash header comparison rather than HMAC-of-body.
        expected = settings.PAYMENT_WEBHOOK_SECRET or ""
        return hmac.compare_digest(expected, signature_header or "")

    def initiate_refund(self, *, provider_reference: str, amount: float) -> dict:
        try:
            response = httpx.post(
                f"{FLUTTERWAVE_BASE_URL}/transactions/{provider_reference}/refund",
                headers=self._headers(),
                json={"amount": amount},
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"Flutterwave initiate_refund failed: {exc}") from exc
