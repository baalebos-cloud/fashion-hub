"""StorageProvider interface for uploads (profile photos, portfolios,
KYC/KYB documents, invoice PDFs)."""
from abc import ABC, abstractmethod


class StorageProvider(ABC):
    @abstractmethod
    def upload(self, *, key: str, file_bytes: bytes, content_type: str, is_public: bool) -> str:
        """Returns a URL (public) or storage key (private, resolved later
        via a signed/proxy URL) for the uploaded object."""
        raise NotImplementedError

    @abstractmethod
    def get_signed_url(self, key: str, expires_in_seconds: int = 300) -> str:
        """Used for private objects such as KYC/KYB documents."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        raise NotImplementedError
