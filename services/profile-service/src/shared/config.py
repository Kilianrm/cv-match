from dataclasses import dataclass
from typing import Optional
import os


@dataclass(frozen=True)
class Settings:
    service_name: str = os.getenv("SERVICE_NAME", "profile-service")
    service_port: int = int(os.getenv("SERVICE_PORT", "8080"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    postgres_host: str = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "profile_db")
    postgres_user: str = os.getenv("POSTGRES_USER", "profile_user")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "profile_pass")
    database_url: str = os.getenv(
        "DATABASE_URL",
        f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}",
    )
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_endpoint_url: Optional[str] = os.getenv("AWS_ENDPOINT_URL") or None
    cv_bucket_name: str = os.getenv("CV_BUCKET_NAME", "profile-cv-bucket")


settings = Settings()
