"""Factory for resolving the configured DeliveryProvider."""
from functools import lru_cache

from app.core.config import settings
from app.integrations.delivery.base import DeliveryProvider
from app.integrations.delivery.provider import InternalDeliveryProvider

_PROVIDERS = {
    "internal": InternalDeliveryProvider,
    # Register external couriers here as they're integrated, e.g.:
    # "provider_a": ProviderADeliveryProvider,
}


@lru_cache
def get_delivery_provider() -> DeliveryProvider:
    provider_cls = _PROVIDERS.get(settings.DELIVERY_PROVIDER)
    if provider_cls is None:
        raise ValueError(f"Unknown DELIVERY_PROVIDER '{settings.DELIVERY_PROVIDER}'")
    return provider_cls()
