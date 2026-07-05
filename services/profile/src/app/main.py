"""Profile Service API entrypoint.

This module exposes:
- Health endpoint for container/service checks.
- Internal endpoints for CV upload, user sync, and profile upsert.
"""

import contextvars
import json
import logging
import time
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from psycopg.errors import UndefinedColumn, UndefinedTable


from src.shared.config import settings
from src.shared.cv_validation import validate_cv_file
from src.shared.s3_storage import S3Storage, StorageBootstrapError
from src.modules.catalogs.cities_store import CitiesStore
from src.modules.catalogs.countries_store import CountriesStore
from src.modules.catalogs.degree_types_store import DegreeTypesStore
from src.modules.catalogs.regions_store import RegionsStore
from src.modules.catalogs.roles_store import RolesStore
from src.modules.catalogs.skills_store import SkillsStore
from src.modules.profile.profile_store import ProfileStore
from src.modules.users.users_store import UsersStore

REQUEST_ID_HEADER = "x-request-id"
TRACE_ID_HEADER = "x-trace-id"

_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
_trace_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()
        record.trace_id = _trace_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service_name": settings.service_name,
            "environment": settings.environment,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "trace_id": getattr(record, "trace_id", "-"),
        }

        optional_fields = (
            "event",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "client_ip",
            "user_agent",
            "user_id",
            "storage_key",
            "size_bytes",
            "user_created",
        )
        for field in optional_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestContextFilter())

    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))


def _new_correlation_id() -> str:
    return str(uuid4())


def _should_log_request_completion(path: str, status_code: int) -> bool:
    # Suppress high-frequency ALB health-check noise while preserving failures.
    return not (path == "/health" and status_code < 400)


configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.service_name,
    description="Internal profile-service API.",
    version="0.1.0",
)


def _database_bootstrap_error_response(request: Request, exc: Exception) -> JSONResponse:
    diag = getattr(exc, "diag", None)
    table_name = getattr(diag, "table_name", None)
    column_name = getattr(diag, "column_name", None)

    logger.error(
        "database bootstrap or schema migration is incomplete",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={
            "event": "database_bootstrap_incomplete",
            "method": request.method,
            "path": request.url.path,
        },
    )

    missing_parts = [part for part in (table_name, column_name) if part]
    missing_label = ".".join(missing_parts) if missing_parts else None
    detail = "Database schema is not ready. Run the bootstrap step before calling this API."
    if missing_label:
        detail = f"{detail} Missing database object: {missing_label}."

    return JSONResponse(
        status_code=503,
        content={
            "detail": detail,
            "error_code": "database_bootstrap_incomplete",
        },
    )


@app.exception_handler(UndefinedTable)
async def undefined_table_handler(request: Request, exc: UndefinedTable) -> JSONResponse:
    return _database_bootstrap_error_response(request, exc)


@app.exception_handler(UndefinedColumn)
async def undefined_column_handler(request: Request, exc: UndefinedColumn) -> JSONResponse:
    return _database_bootstrap_error_response(request, exc)


@app.exception_handler(StorageBootstrapError)
async def storage_bootstrap_handler(request: Request, exc: StorageBootstrapError) -> JSONResponse:
    logger.error(
        "storage bootstrap is incomplete",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={
            "event": "storage_bootstrap_incomplete",
            "method": request.method,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=503,
        content={
            "detail": str(exc),
            "error_code": "storage_bootstrap_incomplete",
        },
    )


def _bootstrap_readiness_snapshot() -> dict:
    try:
        countries_store.get_countries(limit=1)
    except (UndefinedTable, UndefinedColumn):
        return {
            "ready": False,
            "error_code": "database_bootstrap_incomplete",
        }

    return {
        "ready": True,
        "error_code": None,
    }


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get(REQUEST_ID_HEADER) or _new_correlation_id()
    trace_id = request.headers.get(TRACE_ID_HEADER) or request_id

    request_id_token = _request_id_ctx.set(request_id)
    trace_id_token = _trace_id_ctx.set(trace_id)

    started_at = time.perf_counter()
    response = None
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        logger.exception(
            "request failed with unhandled error",
            extra={
                "event": "request_error",
                "method": request.method,
                "path": request.url.path,
            },
        )
        raise
    finally:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        client_ip = request.client.host if request.client else None

        if _should_log_request_completion(request.url.path, status_code):
            logger.info(
                "request completed",
                extra={
                    "event": "request_complete",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                    "user_agent": request.headers.get("user-agent"),
                },
            )

        if response is not None:
            response.headers[REQUEST_ID_HEADER] = request_id
            response.headers[TRACE_ID_HEADER] = trace_id

        _request_id_ctx.reset(request_id_token)
        _trace_id_ctx.reset(trace_id_token)


storage = S3Storage()
users_store = UsersStore(settings.database_url)
profile_store = ProfileStore(settings.database_url)

countries_store = CountriesStore(settings.database_url)
regions_store = RegionsStore(settings.database_url)
cities_store = CitiesStore(settings.database_url)
skills_store = SkillsStore(settings.database_url)
roles_store = RolesStore(settings.database_url)
degree_types_store = DegreeTypesStore(settings.database_url)


@app.get(
    "/internal/locations/countries",
    summary="List all countries",
    description="Returns all countries in the location catalog.",
)
async def list_countries(limit: int = 500) -> dict:
    """Return all countries, optionally limited."""
    countries = countries_store.get_countries(limit=limit)
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
    regions = regions_store.get_regions(country_code=country_code, limit=limit)
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
    cities = cities_store.get_cities(country_code=country_code, region_id=region_id, limit=limit)
    return {
        "status": "ok",
        "count": len(cities),
        "limit": limit,
        "country_code_filter": country_code,
        "region_id_filter": region_id,
        "cities": cities,
    }


@app.get(
    "/internal/catalogs/skills",
    summary="List skills",
    description="Returns skills catalog with optional text and category filters.",
)
async def list_skills_catalog(q: Optional[str] = None, category: Optional[str] = None, limit: int = 200) -> dict:
    skills = skills_store.get_skills(q=q, category=category, limit=limit)
    return {
        "status": "ok",
        "count": len(skills),
        "limit": limit,
        "q_filter": q,
        "category_filter": category,
        "skills": skills,
    }


@app.get(
    "/internal/catalogs/roles",
    summary="List roles",
    description="Returns roles catalog with optional text and category filters.",
)
async def list_roles_catalog(q: Optional[str] = None, category: Optional[str] = None, limit: int = 200) -> dict:
    roles = roles_store.get_roles(q=q, category=category, limit=limit)
    return {
        "status": "ok",
        "count": len(roles),
        "limit": limit,
        "q_filter": q,
        "category_filter": category,
        "roles": roles,
    }


@app.get(
    "/internal/catalogs/degree-types",
    summary="List degree types",
    description="Returns degree type catalog with optional text filter.",
)
async def list_degree_types_catalog(q: Optional[str] = None, limit: int = 200) -> dict:
    degree_types = degree_types_store.get_degree_types(q=q, limit=limit)
    return {
        "status": "ok",
        "count": len(degree_types),
        "limit": limit,
        "q_filter": q,
        "degree_types": degree_types,
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
    summary: Optional[str] = Field(default=None, description="Professional summary")
    country_code: Optional[str] = Field(default=None, description="ISO 3166-1 alpha-2 country code")
    region_id: Optional[str] = Field(default=None, description="Region UUID")
    city_id: Optional[str] = Field(default=None, description="City UUID")
    years_experience: Optional[int] = Field(default=None, description="Years of professional experience")
    work_mode_preference: Optional[str] = Field(default=None, description="Preferred work mode")
    location: Optional[str] = Field(default=None, description="Legacy free-text location")


class SkillRequest(BaseModel):
    skill_name: str = Field(..., description="Skill label")
    proficiency_level: Optional[str] = Field(default=None, description="Optional proficiency level")


class PreferredRoleRequest(BaseModel):
    role_name: str = Field(..., description="Preferred role name")
    role_id: Optional[str] = Field(default=None, description="Optional role UUID from roles catalog")


class ExperienceRequest(BaseModel):
    position: str = Field(..., description="Job position")
    company: str = Field(..., description="Company name")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")
    is_current: bool = Field(default=False, description="Whether this is current role")
    responsibilities: list[str] = Field(default_factory=list, description="List of responsibilities")


class EducationRequest(BaseModel):
    degree_type_id: Optional[str] = Field(default=None, description="Optional degree type UUID from degree catalog")
    degree: str = Field(..., description="Degree title")
    institution: str = Field(..., description="Institution name")
    start_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")
    status: Optional[str] = Field(default=None, description="Education status")


class CertificationRequest(BaseModel):
    name: str = Field(..., description="Certification name")
    issuer: str = Field(..., description="Certification issuer")
    issued_at: Optional[str] = Field(default=None, description="Issued date (YYYY-MM-DD)")
    expires_at: Optional[str] = Field(default=None, description="Expiry date (YYYY-MM-DD)")


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
        "bootstrap": _bootstrap_readiness_snapshot(),
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

    object_key = f"cv/{user_id}/{file.filename}"
    storage.upload_bytes(object_key, content, file.content_type)

    try:
        upload_record = profile_store.register_cv_upload(
            user_id=user_id,
            original_filename=file.filename,
            storage_key=object_key,
            content_type=file.content_type or "application/octet-stream",
            parse_status="pending",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    logger.info(
        "cv upload accepted",
        extra={
            "event": "cv_upload",
            "user_id": user_id,
            "storage_key": object_key,
            "size_bytes": len(content),
        },
    )

    return {
        "status": "accepted",
        "user_id": user_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "bucket": settings.cv_bucket_name,
        "object_key": object_key,
        "cv_upload_record": upload_record,
    }


@app.get(
    "/internal/users/{user_id}/cv",
    summary="Get user's active CV",
    description="Retrieves metadata about the user's currently active CV upload.",
)
async def get_cv(user_id: str) -> dict:
    try:
        cv_record = profile_store.get_active_cv(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if cv_record is None:
        raise HTTPException(status_code=404, detail="No active CV found")

    return {
        "status": "success",
        "cv": cv_record,
    }


@app.delete(
    "/internal/users/{user_id}/cv",
    summary="Delete user's active CV",
    description="Deletes the user's currently active CV metadata and removes file from storage.",
)
async def delete_cv(user_id: str) -> dict:
    try:
        cv_record = profile_store.get_active_cv(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if cv_record is None:
        raise HTTPException(status_code=404, detail="No active CV found")

    storage_key = cv_record.get("storage_key")
    if storage_key:
        storage.delete_object(storage_key)

    profile_store.deactivate_active_cv(user_id)
    logger.info(
        "cv deleted",
        extra={
            "event": "cv_delete",
            "user_id": user_id,
            "storage_key": storage_key,
        },
    )
    return {"status": "deleted", "cv_id": cv_record.get("id")}


@app.post(
    "/internal/users/sync-from-jwt",
    summary="Sync user from JWT",
    description="Synchronizes user identity data from auth claims.",
)
async def sync_from_jwt(payload: SyncFromJwtRequest) -> dict:
    result = users_store.sync_from_jwt(payload.issuer, payload.sub, payload.email)
    logger.info(
        "user sync completed",
        extra={
            "event": "user_sync",
            "user_id": result.internal_user_id,
            "user_created": result.created,
        },
    )
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
    try:
        validated_payload = profile_store.validate_base_profile_payload(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    profile_store.upsert_profile(user_id, validated_payload)
    return {
        "status": "accepted",
        "user_id": user_id,
        "profile": validated_payload,
    }


@app.put(
    "/internal/users/{user_id}/profile",
    summary="Update user profile",
    description="Updates profile data for a specific user.",
)
async def update_profile(user_id: str, payload: UpdateProfileRequest) -> dict:
    try:
        validated_payload = profile_store.validate_base_profile_payload(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    profile_store.upsert_profile(user_id, validated_payload)
    return {
        "status": "accepted",
        "user_id": user_id,
        "profile": validated_payload,
    }


@app.post("/internal/users/{user_id}/skills", summary="Add skill")
async def add_skill(user_id: str, payload: SkillRequest) -> dict:
    try:
        item = profile_store.add_skill(user_id, payload.skill_name, payload.proficiency_level)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if message == "Profile not found" else 409 if "already exists" in message else 422
        raise HTTPException(status_code=status_code, detail=message) from exc
    return {"status": "created", "item": item}


@app.delete("/internal/users/{user_id}/skills/{skill_id}", summary="Remove skill")
async def remove_skill(user_id: str, skill_id: str) -> dict:
    try:
        profile_store.remove_skill(user_id, skill_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404
        raise HTTPException(status_code=status_code, detail=message) from exc
    return {"status": "deleted"}


@app.post("/internal/users/{user_id}/preferred-roles", summary="Add preferred role")
async def add_preferred_role(user_id: str, payload: PreferredRoleRequest) -> dict:
    try:
        item = profile_store.add_preferred_role(user_id, payload.role_name, payload.role_id)
    except ValueError as exc:
        message = str(exc)
        if message == "Profile not found":
            status_code = 404
        elif "already exists" in message:
            status_code = 409
        else:
            status_code = 422
        raise HTTPException(status_code=status_code, detail=message) from exc
    return {"status": "created", "item": item}


@app.put("/internal/users/{user_id}/preferred-roles/{role_id}", summary="Update preferred role")
async def update_preferred_role(user_id: str, role_id: str, payload: PreferredRoleRequest) -> dict:
    try:
        item = profile_store.update_preferred_role(user_id, role_id, payload.role_name, payload.role_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 422
        raise HTTPException(status_code=status_code, detail=message) from exc
    return {"status": "updated", "item": item}


@app.delete("/internal/users/{user_id}/preferred-roles/{role_id}", summary="Delete preferred role")
async def delete_preferred_role(user_id: str, role_id: str) -> dict:
    try:
        profile_store.delete_preferred_role(user_id, role_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted"}


@app.post("/internal/users/{user_id}/experience", summary="Add experience")
async def add_experience(user_id: str, payload: ExperienceRequest) -> dict:
    try:
        item = profile_store.add_experience(user_id, payload.model_dump())
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if message == "Profile not found" else 422
        raise HTTPException(status_code=status_code, detail=message) from exc
    return {"status": "created", "item": item}


@app.put("/internal/users/{user_id}/experience/{experience_id}", summary="Update experience")
async def update_experience(user_id: str, experience_id: str, payload: ExperienceRequest) -> dict:
    try:
        item = profile_store.update_experience(user_id, experience_id, payload.model_dump())
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 422
        raise HTTPException(status_code=status_code, detail=message) from exc
    return {"status": "updated", "item": item}


@app.delete("/internal/users/{user_id}/experience/{experience_id}", summary="Delete experience")
async def delete_experience(user_id: str, experience_id: str) -> dict:
    try:
        profile_store.delete_experience(user_id, experience_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted"}


@app.post("/internal/users/{user_id}/education", summary="Add education")
async def add_education(user_id: str, payload: EducationRequest) -> dict:
    try:
        item = profile_store.add_education(user_id, payload.model_dump())
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if message == "Profile not found" else 422
        raise HTTPException(status_code=status_code, detail=message) from exc
    return {"status": "created", "item": item}


@app.put("/internal/users/{user_id}/education/{education_id}", summary="Update education")
async def update_education(user_id: str, education_id: str, payload: EducationRequest) -> dict:
    try:
        item = profile_store.update_education(user_id, education_id, payload.model_dump())
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 422
        raise HTTPException(status_code=status_code, detail=message) from exc
    return {"status": "updated", "item": item}


@app.delete("/internal/users/{user_id}/education/{education_id}", summary="Delete education")
async def delete_education(user_id: str, education_id: str) -> dict:
    try:
        profile_store.delete_education(user_id, education_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted"}


@app.post("/internal/users/{user_id}/certifications", summary="Add certification")
async def add_certification(user_id: str, payload: CertificationRequest) -> dict:
    try:
        item = profile_store.add_certification(user_id, payload.model_dump())
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if message == "Profile not found" else 422
        raise HTTPException(status_code=status_code, detail=message) from exc
    return {"status": "created", "item": item}


@app.put("/internal/users/{user_id}/certifications/{cert_id}", summary="Update certification")
async def update_certification(user_id: str, cert_id: str, payload: CertificationRequest) -> dict:
    try:
        item = profile_store.update_certification(user_id, cert_id, payload.model_dump())
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 422
        raise HTTPException(status_code=status_code, detail=message) from exc
    return {"status": "updated", "item": item}


@app.delete("/internal/users/{user_id}/certifications/{cert_id}", summary="Delete certification")
async def delete_certification(user_id: str, cert_id: str) -> dict:
    try:
        profile_store.delete_certification(user_id, cert_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted"}
