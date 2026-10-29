"""
S3-compatible object storage implementation (works with any S3-compatible
provider such as MinIO, Backblaze B2, DigitalOcean Spaces, or Hetzner Object
Storage -- deliberately not tied to AWS specifically). Falls back to local
disk storage in development when STORAGE_PROVIDER=local.
"""
import os
import uuid

from app.core.config import settings
from app.core.exceptions import ExternalProviderError
from app.integrations.storage.base import StorageProvider

LOCAL_STORAGE_DIR = "/tmp/fashion-hub-uploads"


class LocalStorageProvider(StorageProvider):
    """Development-only fallback -- never use in production."""

    def upload(self, *, key: str, file_bytes: bytes, content_type: str, is_public: bool) -> str:
        os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)
        path = os.path.join(LOCAL_STORAGE_DIR, key.replace("/", "_"))
        with open(path, "wb") as f:
            f.write(file_bytes)
        return key

    def get_signed_url(self, key: str, expires_in_seconds: int = 300) -> str:
        return f"{settings.APP_URL}/local-uploads/{key}"

    def delete(self, key: str) -> None:
        path = os.path.join(LOCAL_STORAGE_DIR, key.replace("/", "_"))
        if os.path.exists(path):
            os.remove(path)



class PostgresStorageProvider(StorageProvider):
    """Small uploads stored in existing PostgreSQL. No S3 credentials required."""

    def upload(self, *, key: str, file_bytes: bytes, content_type: str, is_public: bool) -> str:
        import uuid
        from sqlalchemy import insert
        from app.core.database import engine
        from app.models.stored_media import StoredMedia
        try:
            owner_id = uuid.UUID(key.split("/")[1])
        except (ValueError, IndexError) as exc:
            raise ExternalProviderError("Invalid media ownership key.") from exc
        media_id = uuid.uuid4()
        with engine.begin() as conn:
            conn.execute(insert(StoredMedia).values(
                id=media_id, owner_user_id=owner_id, storage_key=key,
                content_type=content_type, is_public=is_public, content=file_bytes,
            ))
        if is_public:
            return f"{settings.APP_URL.rstrip('/')}{settings.API_PREFIX}/media/files/{media_id}"
        return key

    def get_signed_url(self, key: str, expires_in_seconds: int = 300) -> str:
        # Private records must be accessed by an authenticated API, not a
        # public or unsigned link. Call the admin preview endpoint instead.
        raise ExternalProviderError("Private database media requires authenticated preview.")

    def delete(self, key: str) -> None:
        from sqlalchemy import delete
        from app.core.database import engine
        from app.models.stored_media import StoredMedia
        with engine.begin() as conn:
            conn.execute(delete(StoredMedia).where(StoredMedia.storage_key == key))


class S3CompatibleStorageProvider(StorageProvider):
    def __init__(self):
        try:
            import boto3
        except ImportError as exc:
            raise ExternalProviderError("The 'boto3' package is not installed.") from exc

        endpoint = (settings.STORAGE_ENDPOINT or "").strip()
        if not endpoint.startswith(("https://", "http://")):
            raise ExternalProviderError("S3 storage endpoint is missing or invalid; configure STORAGE_ENDPOINT.")
        if not settings.STORAGE_BUCKET or not settings.STORAGE_ACCESS_KEY or not settings.STORAGE_SECRET_KEY:
            raise ExternalProviderError("S3 storage credentials or bucket are missing.")
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.STORAGE_ACCESS_KEY,
            aws_secret_access_key=settings.STORAGE_SECRET_KEY,
        )
        self._bucket = settings.STORAGE_BUCKET

    def upload(self, *, key: str, file_bytes: bytes, content_type: str, is_public: bool) -> str:
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=file_bytes,
                ContentType=content_type,

            )
        except Exception as exc:  # noqa: BLE001
            raise ExternalProviderError("Object storage upload failed. Verify bucket credentials and write access.") from exc

        if is_public and settings.STORAGE_PUBLIC_BASE_URL:
            return f"{settings.STORAGE_PUBLIC_BASE_URL.rstrip('/')}/{key}"
        return key

    def get_signed_url(self, key: str, expires_in_seconds: int = 300) -> str:
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            raise ExternalProviderError(f"Presigned URL generation failed: {exc}") from exc

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except Exception as exc:  # noqa: BLE001
            raise ExternalProviderError(f"Object storage delete failed: {exc}") from exc


def build_object_key(*, folder: str, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    return f"{folder}/{uuid.uuid4()}.{ext}"


def get_storage_provider() -> StorageProvider:
    if settings.STORAGE_PROVIDER == "postgres":
        return PostgresStorageProvider()
    if settings.STORAGE_PROVIDER == "local":
        return LocalStorageProvider()
    return S3CompatibleStorageProvider()
