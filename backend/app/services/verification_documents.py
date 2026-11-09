"""Reading private KYC/KYB documents back from storage (admin viewing and the AI document check)."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.exceptions import ExternalProviderError

logger = logging.getLogger(__name__)
PRIVATE_PREFIXES = ("kyc/", "kyb/")


def read_private_document(db: Session, storage_key: str) -> tuple[bytes, str] | None:
    """(bytes, content type), or None when the key isn't a private document or the file is gone."""
    from app.models.stored_media import StoredMedia
    if not storage_key or not storage_key.startswith(PRIVATE_PREFIXES):
        return None
    media = db.query(StoredMedia).filter(StoredMedia.storage_key == storage_key).first()
    if media is not None:
        return (None if media.is_public else (bytes(media.content), media.content_type))
    from app.integrations.storage.object_storage import get_storage_provider
    try:
        return get_storage_provider().read(storage_key)
    except ExternalProviderError:
        logger.warning("verification_document_unreadable")  # no key: it contains the owner's id
        return None
