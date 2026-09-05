"""MinIO client singleton and object helpers, shared by the API and worker processes.

Every generated artefact (invoice / credit-note PDFs, report exports) is written
here and only ever read back through an authenticated endpoint that streams the
object — nothing is served straight off the filesystem and no bucket is public.
"""

import io
from datetime import timedelta
from functools import lru_cache

from minio import Minio
from minio.error import S3Error

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


def put_object(key: str, data: bytes, *, content_type: str = "application/octet-stream") -> str:
    """Upload `data` under `key` in the configured bucket. Returns the key."""
    client = get_minio_client()
    client.put_object(
        settings.minio_bucket,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return key


def object_exists(key: str) -> bool:
    client = get_minio_client()
    try:
        client.stat_object(settings.minio_bucket, key)
        return True
    except S3Error:
        return False


def get_object_bytes(key: str) -> bytes:
    """Download the whole object into memory. Invoices are a few KB — fine to buffer."""
    client = get_minio_client()
    response = client.get_object(settings.minio_bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def presigned_get_url(key: str, *, expires: timedelta = timedelta(minutes=10)) -> str:
    """A short-lived direct download URL. Only handed out to an already-authenticated
    principal that has passed the endpoint's own ownership / permission checks."""
    client = get_minio_client()
    return client.presigned_get_object(settings.minio_bucket, key, expires=expires)
