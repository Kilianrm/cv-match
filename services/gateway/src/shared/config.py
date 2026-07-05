from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    service_name: str = os.getenv("SERVICE_NAME", "gateway")
    environment: str = os.getenv("ENVIRONMENT", "dev")
    service_port: int = int(os.getenv("SERVICE_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Internal service URLs
    profile_service_url: str = os.getenv("PROFILE_SERVICE_URL", "http://profile-service:8080")

    # Cognito (required in production)
    cognito_client_id: str = os.getenv("COGNITO_CLIENT_ID", "")
    jwks_url: str = os.getenv("JWKS_URL", "")

    # Local development: bypass JWT verification
    local_auth_bypass: bool = os.getenv("LOCAL_AUTH_BYPASS", "false").lower() == "true"
    local_user_sub: str = os.getenv("LOCAL_USER_SUB", "local-user-sub")
    local_user_email: str = os.getenv("LOCAL_USER_EMAIL", "local@example.com")
    local_user_issuer: str = os.getenv("LOCAL_USER_ISSUER", "http://local-cognito")


settings = Settings()
