import uuid
from datetime import timedelta

import structlog
from django.conf import settings
from minio import Minio
from minio.error import S3Error

logger = structlog.get_logger(__name__)

_client: Minio = None


def _get_client() -> Minio:
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_USE_SSL,
    )


def get_client() -> Minio:
    global _client
    if _client is None:
        _client = _get_client()
    return _client


def _get_bucket(private: bool) -> str:
    if private:
        return settings.MINIO_PRIVATE_BUCKET
    return settings.MINIO_PUBLIC_BUCKET


def generate_object_key(prefix: str, filename: str) -> str:
    unique_prefix = str(uuid.uuid4())[:8]
    safe_filename = filename.replace(" ", "-").lower()
    return f"{prefix}/{unique_prefix}-{safe_filename}"


def upload_file(file, prefix: str, content_type: str, private: bool = False) -> str:
    client = get_client()
    bucket = _get_bucket(private)
    key = generate_object_key(prefix, file.name)

    try:
        client.put_object(
            bucket_name=bucket,
            object_name=key,
            data=file,
            length=file.size,
            content_type=content_type,
        )
        logger.info(
            "file_uploaded",
            bucket=bucket,
            key=key,
            content_type=content_type,
            size=file.size,
        )
        return key
    except S3Error as e:
        logger.error("minio_upload_failed", bucket=bucket, key=key, error=str(e))
        raise


def get_public_url(key: str) -> str:
    protocol = "https" if settings.MINIO_USE_SSL else "http"
    return (
        f"{protocol}://{settings.MINIO_ENDPOINT}/{settings.MINIO_PUBLIC_BUCKET}/{key}"
    )


def generate_presigned_url(
    key: str, private: bool = True, expiry_minutes: int = 15
) -> str:
    client = get_client()
    bucket = _get_bucket(private)
    try:
        url = client.presigned_get_object(
            bucket_name=bucket,
            object_name=key,
            expires=timedelta(minutes=expiry_minutes),
        )
        logger.info(
            "presigned_url_generated",
            bucket=bucket,
            key=key,
            expiry_minutes=expiry_minutes,
        )
        return url
    except S3Error as e:
        logger.error("presigned_url_failed", bucket=bucket, key=key, error=str(e))
        raise


def delete_file(key: str, private: bool = False) -> None:
    client = get_client()
    bucket = _get_bucket(private)

    try:
        client.remove_object(
            bucket_name=bucket,
            object_name=key,
        )
        logger.info("file_deleted", bucket=bucket, key=key)
    except S3Error as e:
        logger.error("minio_delete_failed", bucket=bucket, key=key, error=str(e))
        raise
