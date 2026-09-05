"""MinIO client singleton and bucket helpers, shared by the API and worker processes."""

from functools import lru_cache

from minio import Minio

from app.config.settings import settings


@lru_cache
def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket() -> None:
    """Creates the configured bucket if it doesn't exist yet. Safe to call repeatedly."""
    client = get_minio_client()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)
