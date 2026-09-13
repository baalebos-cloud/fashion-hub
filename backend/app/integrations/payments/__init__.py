"""
Factory for resolving the configured PaymentProvider. Services should call
`get_payment_provider()` rather than importing a concrete class, so
PAYMENT_PROVIDER can be switched via env var alone.
"""
from functools import lru_cache

from app.core.config import settings
from app.integrations.payments.base import PaymentProvider
from app.integrations.payments.flutterwave import FlutterwaveProvider
from app.integrations.payments.paystack import PaystackProvider

_PROVIDERS = {
    "paystack": PaystackProvider,
    "flutterwave": FlutterwaveProvider,
}


@lru_cache
def get_payment_provider() -> PaymentProvider:
    provider_cls = _PROVIDERS.get(settings.PAYMENT_PROVIDER)
    if provider_cls is None:
        raise ValueError(f"Unknown PAYMENT_PROVIDER '{settings.PAYMENT_PROVIDER}'")
    return provider_cls()
