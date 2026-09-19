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


"""Separate factory for NIN identity lookups (distinct from the
document-review KYCProvider above, which handles ID-photo upload +
admin review, not a live government-database lookup)."""
from app.integrations.kyc.manual_nin import ManualNINProvider
from app.integrations.kyc.nin_provider import NINVerificationProvider
from app.integrations.kyc.prembly import PremblyNINProvider

_NIN_PROVIDERS = {
    "manual": ManualNINProvider,
    "prembly": PremblyNINProvider,
}


@lru_cache
def get_nin_provider() -> NINVerificationProvider:
    provider_cls = _NIN_PROVIDERS.get(settings.NIN_PROVIDER, ManualNINProvider)
    return provider_cls()
