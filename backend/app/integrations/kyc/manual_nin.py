"""
Fallback NIN "provider" for local development or an admin-manual-review
flow when no NIN_API_KEY is configured. Always raises rather than
fabricating identity data -- there is no safe default here; either a real
provider is configured, or NIN submission is blocked with a clear error
rather than silently accepting unverified data.
"""
from app.core.exceptions import ExternalProviderError
from app.integrations.kyc.nin_provider import NINVerificationProvider, NINVerificationResult


class ManualNINProvider(NINVerificationProvider):
    def verify(self, nin_number: str) -> NINVerificationResult:
        raise ExternalProviderError(
            "NIN verification is not configured on this server. Set NIN_PROVIDER and NIN_API_KEY."
        )
