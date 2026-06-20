"""Integration tests for CV upload with LocalStack S3."""

import boto3
from moto import mock_aws

from src.shared.config import settings
from src.shared.s3_storage import S3Storage


@mock_aws
def test_cv_upload_stores_file_in_s3():
    """Verify a valid CV is stored in LocalStack S3."""
    storage = S3Storage()
    
    # Create bucket in mock S3
    storage.ensure_bucket()
    
    # Prepare valid CV content
    user_id = "u-integration-1"
    content = b"Curriculum Vitae\nExperience: 5 years\nSkills: Python, AWS"
    object_key = f"cv/{user_id}"
    
    # Upload to S3
    storage.upload_bytes(object_key, content, "text/plain")
    
    # Verify object exists
    s3 = boto3.client(
        "s3",
        region_name=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    
    try:
        response = s3.head_object(Bucket=settings.cv_bucket_name, Key=object_key)
        assert response["ContentLength"] == len(content)
    except s3.exceptions.NoSuchKey:
        raise AssertionError(f"Object {object_key} not found in S3")
