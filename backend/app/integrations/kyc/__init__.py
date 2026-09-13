"""Factory for resolving the configured KYCProvider."""
from functools import lru_cache

from app.core.config import settings
from app.integrations.kyc.base import KYCProvider
from app.integrations.kyc.provider import ManualReviewKYCProvider

_PROVIDERS = {
    "manual": ManualReviewKYCProvider,
}


@lru_cache
def get_kyc_provider() -> KYCProvider:
    provider_cls = _PROVIDERS.get(settings.KYC_PROVIDER, ManualReviewKYCProvider)
    return provider_cls()
