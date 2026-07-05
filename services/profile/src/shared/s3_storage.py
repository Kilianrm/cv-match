import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from src.shared.config import settings

logger = logging.getLogger(__name__)


class StorageBootstrapError(RuntimeError):
    """Raised when required storage resources are missing or unavailable."""


class S3Storage:
    def __init__(self) -> None:
        client_kwargs: dict[str, str] = {"region_name": settings.aws_region}

        if settings.aws_endpoint_url:
            client_kwargs["endpoint_url"] = settings.aws_endpoint_url
            client_kwargs["aws_access_key_id"] = "test"
            client_kwargs["aws_secret_access_key"] = "test"

        self._s3 = boto3.client("s3", **client_kwargs)

    def ensure_bucket(self) -> None:
        bucket = settings.cv_bucket_name
        try:
            self._s3.head_bucket(Bucket=bucket)
        except ClientError as exc:
            logger.error(
                "Bucket %s is not available. Resources must be provisioned via bootstrap.",
                bucket,
                extra={"event": "s3_bucket_missing", "bucket": bucket},
            )
            raise StorageBootstrapError(
                f"S3 bucket '{bucket}' is not available. Run infrastructure bootstrap before using this endpoint."
            ) from exc

    def upload_bytes(self, object_key: str, content: bytes, content_type: Optional[str]) -> str:
        self.ensure_bucket()
        self._s3.put_object(
            Bucket=settings.cv_bucket_name,
            Key=object_key,
            Body=content,
            ContentType=content_type or "application/octet-stream",
        )
        logger.info(
            "s3 upload completed",
            extra={
                "event": "s3_upload",
                "storage_key": object_key,
                "size_bytes": len(content),
            },
        )
        return object_key

    def delete_object(self, object_key: str) -> None:
        self.ensure_bucket()
        self._s3.delete_object(Bucket=settings.cv_bucket_name, Key=object_key)
        logger.info(
            "s3 delete completed",
            extra={
                "event": "s3_delete",
                "storage_key": object_key,
            },
        )
