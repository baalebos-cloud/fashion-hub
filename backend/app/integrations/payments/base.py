"""
PaymentProvider interface. The rest of the app (checkout_service,
payment_service, webhook routes) depends ONLY on this abstract interface,
never on PaystackProvider/FlutterwaveProvider directly, so swapping or
adding a provider never requires touching business logic.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class InitializePaymentResult:
    provider_reference: str
    authorization_url: str  # where to redirect the client to complete payment
    raw_response: dict


@dataclass
class VerifyPaymentResult:
    provider_reference: str
    status: str  # "successful" | "failed" | "pending"
    amount: float
    currency: str
    paid_at: Optional[str]
    raw_response: dict


class PaymentProvider(ABC):
    @abstractmethod
    def initialize_payment(
        self, *, order_id: str, amount: float, currency: str, customer_email: str, callback_url: str
    ) -> InitializePaymentResult:
        """Start a payment session with the provider and return a redirect URL."""
        raise NotImplementedError

    @abstractmethod
    def verify_payment(self, provider_reference: str) -> VerifyPaymentResult:
        """Server-to-server verification -- the ONLY source of truth for
        whether a payment succeeded. Never trust a client-reported status."""
        raise NotImplementedError

    @abstractmethod
    def verify_webhook_signature(self, *, payload: bytes, signature_header: str) -> bool:
        """Cryptographically verify that a webhook actually came from the
        provider before processing it."""
        raise NotImplementedError

    @abstractmethod
    def initiate_refund(self, *, provider_reference: str, amount: float) -> dict:
        raise NotImplementedError
