"""
Paystack implementation of PaymentProvider.
Docs: https://paystack.com/docs/api/
"""
import hashlib
import hmac

import httpx

from app.core.config import settings
from app.core.policies import money_to_minor_units
from app.core.exceptions import ExternalProviderError
from app.integrations.payments.base import (
    InitializePaymentResult,
    PaymentProvider,
    VerifyPaymentResult,
)

PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackProvider(PaymentProvider):
    def __init__(self, secret_key: str | None = None):
        self.secret_key = secret_key or settings.PAYMENT_SECRET_KEY

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.secret_key}", "Content-Type": "application/json"}

    def initialize_payment(
        self, *, order_id: str, amount: float, currency: str, customer_email: str, callback_url: str
    ) -> InitializePaymentResult:
        try:
            response = httpx.post(
                f"{PAYSTACK_BASE_URL}/transaction/initialize",
                headers=self._headers(),
                json={
                    "email": customer_email,
                    "amount": money_to_minor_units(amount),  # Paystack expects kobo
                    "currency": currency,
                    "callback_url": callback_url,
                    "metadata": {"order_id": order_id},
                },
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()["data"]
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"Paystack initialize_payment failed: {exc}") from exc

        return InitializePaymentResult(
            provider_reference=data["reference"],
            authorization_url=data["authorization_url"],
            raw_response=data,
        )

    def verify_payment(self, provider_reference: str) -> VerifyPaymentResult:
        try:
            response = httpx.get(
                f"{PAYSTACK_BASE_URL}/transaction/verify/{provider_reference}",
                headers=self._headers(),
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()["data"]
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"Paystack verify_payment failed: {exc}") from exc

        status_map = {"success": "successful", "failed": "failed", "abandoned": "failed"}
        return VerifyPaymentResult(
            provider_reference=data["reference"],
            status=status_map.get(data["status"], "pending"),
            amount=data["amount"] / 100,
            currency=data["currency"],
            paid_at=data.get("paid_at"),
            raw_response=data,
        )

    def verify_webhook_signature(self, *, payload: bytes, signature_header: str) -> bool:
        # Paystack signs with the account secret key. Missing keys fail closed.
        if not self.secret_key or not signature_header:
            return False
        computed = hmac.new(
            key=self.secret_key.encode(), msg=payload, digestmod=hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(computed, signature_header or "")

    def initiate_refund(self, *, provider_reference: str, amount: float) -> dict:
        try:
            response = httpx.post(
                f"{PAYSTACK_BASE_URL}/refund",
                headers=self._headers(),
                json={"transaction": provider_reference, "amount": money_to_minor_units(amount)},
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"Paystack initiate_refund failed: {exc}") from exc
