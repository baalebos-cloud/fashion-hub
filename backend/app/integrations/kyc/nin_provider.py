"""
NINVerificationProvider: looks up a Nigerian National Identity Number
(NIN) against a government-backed verification service and returns the
official name/DOB/gender on record. This is what makes NIN verification
meaningful rather than decorative -- the person's profile is checked
AGAINST this response (see kyc_service.py::submit), not just stored
alongside it.

NIN itself is highly sensitive PII. Never log a raw NIN, never include it
in an exception message, and never return it in any API response (see
schemas/kyc.py -- KYCStatusResponse has no nin_number field).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class NINVerificationResult:
    nin: str  # only ever held in memory for this one request; never logged
    full_name: str
    date_of_birth: date
    gender: str
    photo_base64: str | None = None


class NINVerificationProvider(ABC):
    @abstractmethod
    def verify(self, nin_number: str) -> NINVerificationResult:
        """Raises ExternalProviderError on lookup failure or an
        NotFoundError-style domain exception if the NIN doesn't exist in
        the government database -- callers should treat 'not found' as a
        hard rejection, not a retryable error."""
        raise NotImplementedError
