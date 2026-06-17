"""JWT verification against Cognito JWKS.

In local development, set LOCAL_AUTH_BYPASS=true to skip verification
and use a simulated user identity configured via LOCAL_USER_* env vars.
"""

import logging
from dataclasses import dataclass

import httpx
from jose import JWTError, jwk, jwt

from src.shared.config import settings

logger = logging.getLogger(__name__)

_jwks_cache: dict | None = None


@dataclass
class TokenClaims:
    sub: str
    issuer: str
    email: str | None


class JwtVerificationError(Exception):
    pass


def _fetch_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    if not settings.jwks_url:
        raise JwtVerificationError("JWKS_URL is not configured")
    try:
        response = httpx.get(settings.jwks_url, timeout=5)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache
    except Exception as exc:
        raise JwtVerificationError(f"Failed to fetch JWKS: {exc}") from exc


def verify_token(token: str) -> TokenClaims:
    """Verify a Cognito JWT and extract claims.

    Raises JwtVerificationError for invalid or expired tokens.
    """
    if settings.local_auth_bypass:
        logger.warning("LOCAL_AUTH_BYPASS is enabled ? skipping JWT verification")
        return TokenClaims(
            sub=settings.local_user_sub,
            issuer=settings.local_user_issuer,
            email=settings.local_user_email,
        )

    try:
        header = jwt.get_unverified_header(token)
        jwks = _fetch_jwks()

        key = next(
            (k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")),
            None,
        )
        if key is None:
            raise JwtVerificationError("No matching key found in JWKS")

        verify_aud = bool(settings.cognito_client_id)
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.cognito_client_id if verify_aud else None,
            options={"verify_aud": verify_aud},
        )

        if claims.get("token_use") not in ("access", None):
            raise JwtVerificationError("Only access tokens are accepted")

        return TokenClaims(
            sub=claims["sub"],
            issuer=claims["iss"],
            email=claims.get("email"),
        )
    except JWTError as exc:
        raise JwtVerificationError(f"Invalid token: {exc}") from exc
