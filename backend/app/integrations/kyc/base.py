"""KYCProvider interface for identity/business verification providers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VerificationSubmissionResult:
    provider_reference: str
    status: str  # pending | under_review | verified | rejected


class KYCProvider(ABC):
    @abstractmethod
    def submit_identity_verification(self, *, user_id: str, id_type: str, document_urls: list[str]) -> VerificationSubmissionResult:
        raise NotImplementedError

    @abstractmethod
    def submit_business_verification(self, *, business_owner_id: str, registration_number: str, document_urls: list[str]) -> VerificationSubmissionResult:
        raise NotImplementedError

    @abstractmethod
    def check_status(self, provider_reference: str) -> str:
        raise NotImplementedError
