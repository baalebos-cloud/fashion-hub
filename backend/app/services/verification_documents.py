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


def profile_photo_source(user, url: str | None = None) -> tuple[str, str] | None:
    """Where an uploaded profile photo lives: ("media", <id>) or ("object", <storage key>), but only for a
    link in the exact form Tailora's own upload returns (no other host, query or #fragment). Anything
    else, such as an outside image with a real photo's id tucked into it, is None: the face check then
    can't pass, because customers would see a different picture from the one compared."""
    import re

    from app.core.config import settings
    url = (url if url is not None else getattr(user, "profile_photo_url", None) or "").strip()
    if not url:
        return None
    uuid_pattern = r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
    prefix = re.escape(settings.API_PREFIX.rstrip("/")) + r"/media/files/" + uuid_pattern
    for allowed in (re.escape(settings.APP_URL.rstrip("/")) + prefix, prefix):
        found = re.fullmatch(allowed, url)
        if found:
            return ("media", found.group(1))
    if settings.STORAGE_PUBLIC_BASE_URL:
        found = re.fullmatch(re.escape(settings.STORAGE_PUBLIC_BASE_URL.rstrip("/"))
                             + r"/(avatar/" + re.escape(str(user.id)) + r"/[A-Za-z0-9-]+\.(?:jpg|jpeg|png|webp))", url)
        if found:
            return ("object", found.group(1))
    return None


def read_profile_photo(db: Session, user, url: str | None = None) -> bytes | None:
    """The bytes of the user's uploaded profile photo (or of `url`, a photo they're switching to), or
    None when the link isn't a genuine Tailora upload of their own."""
    import uuid as _uuid

    from app.models.stored_media import StoredMedia
    source = profile_photo_source(user, url)
    if source is None:
        return None
    kind, value = source
    if kind == "media":
        media = db.get(StoredMedia, _uuid.UUID(value))
        if (media is None or not media.storage_key.startswith(f"avatar/{user.id}/")
                or str(media.owner_user_id) != str(user.id)):
            return None
        return bytes(media.content)
    from app.integrations.storage.object_storage import get_storage_provider
    try:
        return get_storage_provider().read(value)[0]
    except ExternalProviderError:
        return None
