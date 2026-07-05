from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    service_name: str = os.getenv("SERVICE_NAME", "cv-parser-service")
    environment: str = os.getenv("ENVIRONMENT", "dev")
    service_port: int = int(os.getenv("SERVICE_PORT", "8090"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_endpoint_url: str | None = os.getenv("AWS_ENDPOINT_URL") or None

    parser_queue_url: str = os.getenv("PARSER_QUEUE_URL", "")
    parser_dlq_url: str = os.getenv("PARSER_DLQ_URL", "")
    cv_bucket_name: str = os.getenv("CV_BUCKET_NAME", "profile-cv-bucket")
    profile_service_base_url: str = os.getenv("PROFILE_SERVICE_BASE_URL", "http://profile-service:8080")


settings = Settings()
