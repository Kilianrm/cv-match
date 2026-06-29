import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from src.shared.config import settings

logger = logging.getLogger(__name__)


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
        except ClientError:
            logger.info("Bucket %s not found, creating it", bucket)
            self._s3.create_bucket(Bucket=bucket)

    def upload_bytes(self, object_key: str, content: bytes, content_type: Optional[str]) -> str:
        self.ensure_bucket()
        self._s3.put_object(
            Bucket=settings.cv_bucket_name,
            Key=object_key,
            Body=content,
            ContentType=content_type or "application/octet-stream",
        )
        return object_key

    def delete_object(self, object_key: str) -> None:
        self.ensure_bucket()
        self._s3.delete_object(Bucket=settings.cv_bucket_name, Key=object_key)
