"""Profile Service API entrypoint.

This module exposes:
- Health endpoint for container/service checks.
- Internal endpoints for CV upload, user sync, and profile upsert.
"""

import logging
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field


from src.shared.config import settings
from src.shared.cv_validation import validate_cv_file
from src.shared.s3_storage import S3Storage
from src.modules.profile.profile_store import ProfileStore
from src.modules.users.users_store import UsersStore
from src.modules.locations.locations_store import LocationsStore
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(
    title=settings.service_name,
    description="Internal profile-service API.",
    version="0.1.0",
)
storage = S3Storage()
users_store = UsersStore(settings.database_url)
profile_store = ProfileStore(settings.database_url)

locations_store = LocationsStore(settings.database_url)


@app.get(
    "/internal/locations/countries",
    summary="List all countries",
    description="Returns all countries in the location catalog.",
)
async def list_countries(limit: int = 500) -> dict:
    """Return all countries, optionally limited."""
    countries = locations_store.get_countries(limit=limit)
    return {
        "status": "ok",
        "count": len(countries),
        "limit": limit,
        "countries": countries,
    }


@app.get(
    "/internal/locations/regions",
    summary="List regions",
    description="Returns regions, optionally filtered by country code.",
)
async def list_regions(country_code: Optional[str] = None, limit: int = 500) -> dict:
    """Return regions, optionally filtered by country_code query parameter."""
    regions = locations_store.get_regions(country_code=country_code, limit=limit)
    return {
        "status": "ok",
        "count": len(regions),
        "limit": limit,
        "country_code_filter": country_code,
        "regions": regions,
    }


@app.get(
    "/internal/locations/cities",
    summary="List cities",
    description="Returns cities, optionally filtered by country code and/or region ID.",
)
async def list_cities(
    country_code: Optional[str] = None, region_id: Optional[str] = None, limit: int = 500
) -> dict:
    """Return cities, optionally filtered by country_code and/or region_id query parameters."""
    cities = locations_store.get_cities(country_code=country_code, region_id=region_id, limit=limit)
    return {
        "status": "ok",
        "count": len(cities),
        "limit": limit,
        "country_code_filter": country_code,
        "region_id_filter": region_id,
        "cities": cities,
    }

class SyncFromJwtRequest(BaseModel):
    """Payload received from internal auth flow to synchronize a user."""

    issuer: str = Field(..., description="JWT issuer, typically Cognito user pool issuer URL")
    sub: str = Field(..., description="JWT subject claim (stable external user identifier)")
    email: Optional[str] = Field(default=None, description="User primary email")


class UpdateProfileRequest(BaseModel):
    """Payload to upsert profile data for one user."""

    full_name: str = Field(..., description="User full name")
    headline: Optional[str] = Field(default=None, description="Professional headline")
    location: Optional[str] = Field(default=None, description="Current location")


@app.get(
    "/health",
    summary="Service health",
    description="Readiness probe for local and containerized environments.",
)
async def health() -> dict:
    """Return a minimal health snapshot for probes and diagnostics."""

    return {
        "service": settings.service_name,
        "status": "ok",
        "cv_bucket": settings.cv_bucket_name,
    }


@app.post(
    "/internal/users/{user_id}/cv",
    summary="Upload CV",
    description="Accepts a CV file for a specific user and uploads it to S3 (LocalStack in local mode).",
)
async def upload_cv(user_id: str, file: UploadFile = File(...)) -> dict:
    content = await file.read()
    validation = validate_cv_file(file.filename, file.content_type, content)
    if not validation.ok:
        raise HTTPException(status_code=400, detail=validation.reason)

    object_key = f"cv/{user_id}"
    storage.upload_bytes(object_key, content, file.content_type)
    return {
        "status": "accepted",
        "user_id": user_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "bucket": settings.cv_bucket_name,
        "object_key": object_key,
    }


@app.post(
    "/internal/users/sync-from-jwt",
    summary="Sync user from JWT",
    description="Synchronizes user identity data from auth claims.",
)
async def sync_from_jwt(payload: SyncFromJwtRequest) -> dict:
    result = users_store.sync_from_jwt(payload.issuer, payload.sub, payload.email)
    return {
        "status": "accepted",
        "user_id": result.internal_user_id,
        "internal_user_id": result.internal_user_id,
        "created": result.created,
        "issuer": payload.issuer,
        "sub": payload.sub,
        "email": payload.email,
    }


@app.get(
    "/internal/users/{user_id}/profile",
    summary="Get user profile",
    description="Returns profile data for a specific user.",
)
async def get_profile(user_id: str) -> dict:
    profile = profile_store.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.post(
    "/internal/users/{user_id}/profile",
    summary="Upsert user profile",
    description="Creates or updates profile data for a specific user.",
)
async def upsert_profile(user_id: str, payload: UpdateProfileRequest) -> dict:
    profile_store.upsert_profile(user_id, payload.model_dump())
    return {
        "status": "accepted",
        "user_id": user_id,
        "profile": payload.model_dump(),
    }


@app.put(
    "/internal/users/{user_id}/profile",
    summary="Update user profile",
    description="Updates profile data for a specific user.",
)
async def update_profile(user_id: str, payload: UpdateProfileRequest) -> dict:
    profile_store.upsert_profile(user_id, payload.model_dump())
    return {
        "status": "accepted",
        "user_id": user_id,
        "profile": payload.model_dump(),
    }
