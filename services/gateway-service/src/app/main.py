"""Gateway Service entrypoint.

Validates JWT tokens issued by Cognito, then routes requests
to internal services (profile-service, etc.).

Public API prefix: /api/v1
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from src.shared.config import settings
from src.shared.jwt_verifier import JwtVerificationError, TokenClaims, verify_token

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger(__name__)

_http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(application: FastAPI):
    global _http_client
    _http_client = httpx.AsyncClient(
        base_url=settings.profile_service_url,
        timeout=30,
    )
    yield
    await _http_client.aclose()
    _http_client = None


app = FastAPI(
    title="CV Match Gateway",
    description="Public API gateway ? validates auth and routes to internal services.",
    version="0.1.0",
    lifespan=lifespan,
)


def _profile_client() -> httpx.AsyncClient:
    if _http_client is None:
        raise RuntimeError("HTTP client not initialized")
    return _http_client


def _extract_bearer(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return auth.removeprefix("Bearer ").strip()


def _authenticate(request: Request) -> TokenClaims:
    try:
        return verify_token(_extract_bearer(request))
    except JwtVerificationError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


async def _resolve_user_id(claims: TokenClaims) -> str:
    """Sync user with profile-service and return the internal user_id."""
    resp = await _profile_client().post(
        "/internal/users/sync-from-jwt",
        json={"issuer": claims.issuer, "sub": claims.sub, "email": claims.email},
    )
    if resp.status_code != 200:
        logger.error("sync-from-jwt failed: %s ? %s", resp.status_code, resp.text)
        raise HTTPException(status_code=502, detail="Failed to resolve user identity")
    return resp.json()["internal_user_id"]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", summary="Gateway health check")
async def health() -> dict:
    return {"service": settings.service_name, "status": "ok"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/api/v1/auth/session", summary="Start application session")
async def auth_session(request: Request) -> dict:
    """Validate Cognito JWT and ensure the internal user record exists."""
    claims = _authenticate(request)
    resp = await _profile_client().post(
        "/internal/users/sync-from-jwt",
        json={"issuer": claims.issuer, "sub": claims.sub, "email": claims.email},
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="User sync failed")
    data = resp.json()
    return {"status": "authenticated", "is_new_user": data.get("created", False)}


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@app.get("/api/v1/profile", summary="Get authenticated user profile")
async def get_profile(request: Request) -> Any:
    claims = _authenticate(request)
    user_id = await _resolve_user_id(claims)
    resp = await _profile_client().get(f"/internal/users/{user_id}/profile")
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Profile not found")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to retrieve profile")
    return resp.json()


@app.put("/api/v1/profile", summary="Update authenticated user profile")
async def update_profile(request: Request) -> Any:
    claims = _authenticate(request)
    user_id = await _resolve_user_id(claims)
    body = await request.json()
    resp = await _profile_client().put(
        f"/internal/users/{user_id}/profile",
        json=body,
    )
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Profile not found")
    if resp.status_code in (400, 422):
        try:
            detail = resp.json().get("detail", "Invalid profile payload")
        except ValueError:
            detail = "Invalid profile payload"
        raise HTTPException(status_code=resp.status_code, detail=detail)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to update profile")
    return resp.json()


# ---------------------------------------------------------------------------
# CV
# ---------------------------------------------------------------------------

@app.post("/api/v1/cv/upload", summary="Upload CV for authenticated user")
async def upload_cv(request: Request, file: UploadFile = File(...)) -> Any:
    claims = _authenticate(request)
    user_id = await _resolve_user_id(claims)
    content = await file.read()
    resp = await _profile_client().post(
        f"/internal/users/{user_id}/cv",
        files={"file": (file.filename, content, file.content_type)},
    )
    if resp.status_code == 400:
        raise HTTPException(
            status_code=400,
            detail=resp.json().get("detail", "Invalid CV file"),
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="CV upload failed")
    return JSONResponse(status_code=202, content=resp.json())


# ---------------------------------------------------------------------------
# Locations (Public)
# ---------------------------------------------------------------------------

@app.get("/api/v1/locations/countries", summary="List all countries")
async def list_countries(limit: int = 500) -> Any:
    """Return all countries in the location catalog (no authentication required)."""
    resp = await _profile_client().get("/internal/locations/countries", params={"limit": limit})
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to retrieve countries")
    return resp.json()


@app.get("/api/v1/locations/regions", summary="List regions")
async def list_regions(country_code: str | None = None, limit: int = 500) -> Any:
    """Return regions, optionally filtered by country code (no authentication required)."""
    params = {"limit": limit}
    if country_code:
        params["country_code"] = country_code
    resp = await _profile_client().get("/internal/locations/regions", params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to retrieve regions")
    return resp.json()


@app.get("/api/v1/locations/cities", summary="List cities")
async def list_cities(
    country_code: str | None = None, region_id: str | None = None, limit: int = 500
) -> Any:
    """Return cities, optionally filtered by country code and/or region ID (no authentication required)."""
    params = {"limit": limit}
    if country_code:
        params["country_code"] = country_code
    if region_id:
        params["region_id"] = region_id
    resp = await _profile_client().get("/internal/locations/cities", params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to retrieve cities")
    return resp.json()
