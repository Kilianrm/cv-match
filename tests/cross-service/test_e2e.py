#!/usr/bin/env python3
"""Cross-service end-to-end checks for local MVP.

This module is pytest-compatible (test_* functions) and also supports
direct execution via `python3 test_e2e.py` when pytest is unavailable.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request


def http_request(method: str, url: str, *, body: bytes | None = None, headers: dict[str, str] | None = None):
    req = urllib.request.Request(url, data=body, method=method)
    for key, value in (headers or {}).items():
        req.add_header(key, value)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = resp.read().decode("utf-8")
            return resp.status, payload
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        return exc.code, payload


def assert_eq(expected, actual, context: str) -> None:
    if expected != actual:
        raise AssertionError(f"{context}: expected {expected}, got {actual}")


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")
TEST_ENV = os.getenv("TEST_ENV", "local").strip().lower()
DB_CHECK_MODE = os.getenv("DB_CHECK_MODE", "docker" if TEST_ENV == "local" else "none").strip().lower()
DATABASE_URL = os.getenv("DATABASE_URL", "")
PROFILE_POSTGRES_CONTAINER = os.getenv("PROFILE_POSTGRES_CONTAINER", "profile-postgres")
PROFILE_DB_USER = os.getenv("PROFILE_DB_USER", "profile_user")
PROFILE_DB_NAME = os.getenv("PROFILE_DB_NAME", "profile_db")


def api_url(path: str) -> str:
    if not path.startswith("/"):
        raise ValueError(f"path must start with '/': {path}")
    return f"{BASE_URL}{path}"


def wait_for_gateway(timeout_seconds: int = 60) -> None:
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            status, payload = http_request("GET", api_url("/health"))
            if status == 200:
                data = json.loads(payload)
                if data.get("status") == "ok":
                    return
        except (urllib.error.URLError, OSError, TimeoutError):
            # Service can briefly refuse/reset connections while booting.
            pass
        time.sleep(1)
    raise TimeoutError("gateway-service did not become healthy in time")


def wait_for_auth_session(timeout_seconds: int = 45) -> tuple[int, str]:
    start = time.time()
    last_status = None
    last_payload = ""
    while time.time() - start < timeout_seconds:
        status, payload = http_request(
            "POST",
            api_url("/api/v1/auth/session"),
            headers=AUTH_HEADERS,
        )
        last_status = status
        last_payload = payload
        if status == 200:
            return status, payload
        time.sleep(1)
    raise TimeoutError(f"auth/session did not become ready in time (last status={last_status}, body={last_payload})")


def psql_scalar(query: str) -> str:
    if DB_CHECK_MODE == "none":
        raise RuntimeError("database checks are disabled (DB_CHECK_MODE=none)")

    if DB_CHECK_MODE == "database_url":
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is required when DB_CHECK_MODE=database_url")
        try:
            from psycopg import connect
        except ModuleNotFoundError as exc:
            raise RuntimeError("psycopg is required for DB_CHECK_MODE=database_url") from exc

        with connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                row = cur.fetchone()
                return "" if row is None else str(row[0])

    if DB_CHECK_MODE != "docker":
        raise RuntimeError(f"unsupported DB_CHECK_MODE: {DB_CHECK_MODE}")

    cmd = [
        "docker",
        "exec",
        "-i",
        PROFILE_POSTGRES_CONTAINER,
        "psql",
        "-U", PROFILE_DB_USER,
        "-d", PROFILE_DB_NAME,
        "-tA",
        "-c",
        query,
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


AUTH_HEADERS = {"Authorization": f"Bearer {AUTH_TOKEN}"}
TEST_USER_EMAIL: str | None = None


def test_01_gateway_health() -> None:
    print("[1/6] Waiting for gateway-service health")
    wait_for_gateway()


def test_02_auth_session_through_gateway_service() -> None:
    print("[2/6] auth/session through gateway-service")
    status, payload = wait_for_auth_session()
    assert_eq(200, status, "auth/session status code")
    data = json.loads(payload)
    assert_eq("authenticated", data.get("status"), "auth/session payload status")


def test_03_profile_read_before_upsert() -> None:
    print("[3/6] profile read before upsert (allow 404 or existing 200)")
    status, _ = http_request("GET", api_url("/api/v1/profile"), headers=AUTH_HEADERS)
    if status not in (200, 404):
        raise AssertionError(f"initial profile read status code: expected 200 or 404, got {status}")


def test_04_profile_upsert_and_read() -> None:
    global TEST_USER_EMAIL
    print("[4/6] profile upsert through gateway-service")
    update_body = json.dumps(
        {
            "full_name": "Local Test User",
            "headline": "QA Engineer",
            "summary": "Quality focused engineer",
            "country_code": "AT",
            "region_id": "00000003-0000-0000-0000-000000000003",
            "city_id": "10000003-0000-0000-0000-000000000003",
            "years_experience": 4,
            "work_mode_preference": "remote",
            "location": "Vienna",
        }
    ).encode("utf-8")
    status, payload = http_request(
        "PUT",
        api_url("/api/v1/profile"),
        body=update_body,
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
    )
    assert_eq(200, status, "profile update status code")
    data = json.loads(payload)
    assert_eq("accepted", data.get("status"), "profile update payload status")

    print("[5/6] profile read after upsert")
    status, payload = http_request("GET", api_url("/api/v1/profile"), headers=AUTH_HEADERS)
    assert_eq(200, status, "profile read after upsert status code")
    data = json.loads(payload)
    profile = data.get("profile", {})
    user = data.get("user", {})
    location = data.get("location", {})
    assert_eq("Local Test User", profile.get("full_name"), "profile.full_name")
    assert_eq("QA Engineer", profile.get("headline"), "profile.headline")
    assert_eq("Quality focused engineer", profile.get("summary"), "profile.summary")
    assert_eq("AT", profile.get("country_code"), "profile.country_code")
    assert_eq("00000003-0000-0000-0000-000000000003", profile.get("region_id"), "profile.region_id")
    assert_eq("10000003-0000-0000-0000-000000000003", profile.get("city_id"), "profile.city_id")
    assert_eq("4", str(profile.get("years_experience")), "profile.years_experience")
    assert_eq("remote", profile.get("work_mode_preference"), "profile.work_mode_preference")
    assert_eq("Vienna", profile.get("legacy_location"), "profile.legacy_location")
    user_email = user.get("email")
    if not isinstance(user_email, str) or "@" not in user_email:
        raise AssertionError(f"user.email should be a valid email string, got {user_email}")
    TEST_USER_EMAIL = user_email
    assert_eq("AT", (location.get("country") or {}).get("code"), "location.country.code")
    assert_eq("Austria", (location.get("country") or {}).get("name"), "location.country.name")
    assert_eq("00000003-0000-0000-0000-000000000003", (location.get("region") or {}).get("id"), "location.region.id")
    assert_eq("Vienna", (location.get("region") or {}).get("name"), "location.region.name")
    assert_eq("10000003-0000-0000-0000-000000000003", (location.get("city") or {}).get("id"), "location.city.id")
    assert_eq("Vienna", (location.get("city") or {}).get("name"), "location.city.name")

    # Ensure subsection keys exist and are frontend-friendly by default.
    for section in ["skills", "preferred_roles", "experience", "education", "certifications"]:
        if section not in data or not isinstance(data[section], list):
            raise AssertionError(f"expected list section '{section}' in profile payload")


def test_05_cv_upload_through_gateway_service() -> None:
    print("[6/6] CV upload through gateway-service")
    cv_bytes = (
        b"Curriculum Vitae\n"
        b"Experience: Backend APIs and integration testing.\n"
        b"Skills: Python, FastAPI, PostgreSQL.\n"
    )
    # Minimal multipart payload without extra dependencies.
    boundary = "----cvmatchboundary7MA4YWxkTrZu0gW"
    multipart = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"cross_cv.txt\"\r\n"
        f"Content-Type: text/plain\r\n\r\n"
    ).encode("utf-8") + cv_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    status, payload = http_request(
        "POST",
        api_url("/api/v1/profile/cv"),
        body=multipart,
        headers={
            **AUTH_HEADERS,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    assert_eq(202, status, "cv upload status code")
    data = json.loads(payload)
    assert_eq("accepted", data.get("status"), "cv upload payload status")


def test_06_database_rows_persisted() -> None:
    if DB_CHECK_MODE == "none":
        print("Skipping direct DB persistence checks (DB_CHECK_MODE=none)")
        return

    print("Verifying users row exists in PostgreSQL")
    if not TEST_USER_EMAIL:
        raise AssertionError("expected TEST_USER_EMAIL to be set before DB verification")

    safe_email = TEST_USER_EMAIL.replace("'", "''")
    user_count = psql_scalar(f"SELECT count(*) FROM users WHERE email = '{safe_email}';")
    assert_eq("1", user_count, "users row count")

    print("Verifying upserted profile values are persisted in PostgreSQL")
    profile_row = psql_scalar(
        """
        SELECT
            p.full_name || '|' ||
            COALESCE(p.headline, '') || '|' ||
            COALESCE(p.location, '') || '|' ||
            COALESCE(p.country_code, '') || '|' ||
            COALESCE(p.summary, '') || '|' ||
            COALESCE(p.region_id::text, '') || '|' ||
            COALESCE(p.city_id::text, '') || '|' ||
            COALESCE(p.years_experience::text, '') || '|' ||
            COALESCE(p.work_mode_preference, '')
        FROM profiles p
        ORDER BY p.updated_at DESC
        LIMIT 1;
        """
    )
    if not profile_row:
        raise AssertionError("expected at least one persisted profile row")

    parts = profile_row.split("|", 8)
    if len(parts) != 9:
        raise AssertionError(f"unexpected profile row shape: {profile_row}")

    assert_eq("Local Test User", parts[0], "stored profile full_name")
    assert_eq("QA Engineer", parts[1], "stored profile headline")
    assert_eq("Vienna", parts[2], "stored profile location")
    assert_eq("AT", parts[3], "stored profile country_code")
    assert_eq("Quality focused engineer", parts[4], "stored profile summary")
    assert_eq("00000003-0000-0000-0000-000000000003", parts[5], "stored profile region_id")
    assert_eq("10000003-0000-0000-0000-000000000003", parts[6], "stored profile city_id")
    assert_eq("4", parts[7], "stored profile years_experience")
    assert_eq("remote", parts[8], "stored profile work_mode_preference")


def test_07_profile_validation_rejects_invalid_location_hierarchy() -> None:
    print("[7/7] profile update validation rejects city_id without region_id")
    invalid_body = json.dumps(
        {
            "full_name": "Local Test User",
            "headline": "QA Engineer",
            "city_id": "10000003-0000-0000-0000-000000000003",
        }
    ).encode("utf-8")

    status, payload = http_request(
        "PUT",
        api_url("/api/v1/profile"),
        body=invalid_body,
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
    )
    assert_eq(422, status, "invalid profile update status code")
    data = json.loads(payload)
    expected_detail = "region_id is required when city_id is provided"
    assert_eq(expected_detail, data.get("detail"), "invalid profile update detail")


def test_08_profile_subsections_crud() -> None:
    print("[8/8] subsection CRUD through gateway-service")

    skill_create = json.dumps({"skill_name": "Python", "proficiency_level": "advanced"}).encode("utf-8")
    status, payload = http_request(
        "POST",
        api_url("/api/v1/profile/skills"),
        body=skill_create,
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
    )
    assert_eq(201, status, "add skill status code")
    skill_data = json.loads(payload)
    skill_id = skill_data.get("item", {}).get("skill_id")
    if not skill_id:
        raise AssertionError("expected skill_id in add skill response")

    known_role_id = "20000000-0000-0000-0000-000000000002"
    known_degree_type_id = "30000000-0000-0000-0000-000000000003"

    role_create = json.dumps({"role_name": "Backend Engineer", "role_id": known_role_id}).encode("utf-8")
    status, payload = http_request(
        "POST",
        api_url("/api/v1/profile/preferred-roles"),
        body=role_create,
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
    )
    assert_eq(201, status, "add preferred role status code")
    role_item = json.loads(payload).get("item", {})
    role_id = role_item.get("id")
    if not role_id:
        raise AssertionError("expected role id in add preferred role response")
    assert_eq(known_role_id, role_item.get("role_id"), "preferred role role_id")

    role_update = json.dumps({"role_name": "Senior Backend Engineer"}).encode("utf-8")
    status, payload = http_request(
        "PUT",
        api_url(f"/api/v1/profile/preferred-roles/{role_id}"),
        body=role_update,
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
    )
    assert_eq(200, status, "update preferred role status code")
    assert_eq(
        "Senior Backend Engineer",
        json.loads(payload).get("item", {}).get("role_name"),
        "updated preferred role name",
    )

    exp_create = json.dumps(
        {
            "position": "Backend Engineer",
            "company": "Acme",
            "start_date": "2022-01-01",
            "end_date": None,
            "is_current": True,
            "responsibilities": ["Build APIs", "Write tests"],
        }
    ).encode("utf-8")
    status, payload = http_request(
        "POST",
        api_url("/api/v1/profile/experience"),
        body=exp_create,
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
    )
    assert_eq(201, status, "add experience status code")
    experience_id = json.loads(payload).get("item", {}).get("id")
    if not experience_id:
        raise AssertionError("expected experience id in add experience response")

    exp_update = json.dumps(
        {
            "position": "Backend Engineer",
            "company": "Acme Corp",
            "start_date": "2022-01-01",
            "end_date": "2024-12-31",
            "is_current": False,
            "responsibilities": ["Build APIs"],
        }
    ).encode("utf-8")
    status, payload = http_request(
        "PUT",
        api_url(f"/api/v1/profile/experience/{experience_id}"),
        body=exp_update,
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
    )
    assert_eq(200, status, "update experience status code")
    assert_eq("Acme Corp", json.loads(payload).get("item", {}).get("company"), "updated experience company")

    edu_create = json.dumps(
        {
            "degree": "BSc Computer Science",
            "institution": "TU Vienna",
            "start_date": "2018-09-01",
            "end_date": "2021-06-30",
            "status": "completed",
            "degree_type_id": known_degree_type_id,
        }
    ).encode("utf-8")
    status, payload = http_request(
        "POST",
        api_url("/api/v1/profile/education"),
        body=edu_create,
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
    )
    assert_eq(201, status, "add education status code")
    education_item = json.loads(payload).get("item", {})
    education_id = education_item.get("id")
    if not education_id:
        raise AssertionError("expected education id in add education response")
    assert_eq(known_degree_type_id, education_item.get("degree_type_id"), "education degree_type_id")

    edu_update = json.dumps(
        {
            "degree": "MSc Computer Science",
            "institution": "TU Vienna",
            "start_date": "2021-09-01",
            "end_date": None,
            "status": "in_progress",
            "degree_type_id": known_degree_type_id,
        }
    ).encode("utf-8")
    status, payload = http_request(
        "PUT",
        api_url(f"/api/v1/profile/education/{education_id}"),
        body=edu_update,
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
    )
    assert_eq(200, status, "update education status code")
    assert_eq("MSc Computer Science", json.loads(payload).get("item", {}).get("degree"), "updated education degree")

    cert_create = json.dumps(
        {
            "name": "AWS Certified Developer",
            "issuer": "Amazon",
            "issued_at": "2024-01-15",
            "expires_at": "2027-01-15",
        }
    ).encode("utf-8")
    status, payload = http_request(
        "POST",
        api_url("/api/v1/profile/certifications"),
        body=cert_create,
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
    )
    assert_eq(201, status, "add certification status code")
    cert_id = json.loads(payload).get("item", {}).get("id")
    if not cert_id:
        raise AssertionError("expected certification id in add certification response")

    cert_update = json.dumps(
        {
            "name": "AWS Certified Developer Associate",
            "issuer": "Amazon",
            "issued_at": "2024-01-15",
            "expires_at": "2027-01-15",
        }
    ).encode("utf-8")
    status, payload = http_request(
        "PUT",
        api_url(f"/api/v1/profile/certifications/{cert_id}"),
        body=cert_update,
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
    )
    assert_eq(200, status, "update certification status code")
    assert_eq(
        "AWS Certified Developer Associate",
        json.loads(payload).get("item", {}).get("name"),
        "updated certification name",
    )

    status, _ = http_request("DELETE", api_url(f"/api/v1/profile/skills/{skill_id}"), headers=AUTH_HEADERS)
    assert_eq(204, status, "delete skill status code")
    status, _ = http_request("DELETE", api_url(f"/api/v1/profile/preferred-roles/{role_id}"), headers=AUTH_HEADERS)
    assert_eq(204, status, "delete preferred role status code")
    status, _ = http_request("DELETE", api_url(f"/api/v1/profile/experience/{experience_id}"), headers=AUTH_HEADERS)
    assert_eq(204, status, "delete experience status code")
    status, _ = http_request("DELETE", api_url(f"/api/v1/profile/education/{education_id}"), headers=AUTH_HEADERS)
    assert_eq(204, status, "delete education status code")
    status, _ = http_request("DELETE", api_url(f"/api/v1/profile/certifications/{cert_id}"), headers=AUTH_HEADERS)
    assert_eq(204, status, "delete certification status code")

    status, payload = http_request("GET", api_url("/api/v1/profile"), headers=AUTH_HEADERS)
    assert_eq(200, status, "profile read after subsection deletes status code")
    data = json.loads(payload)
    assert_eq(0, len(data.get("skills", [])), "skills should be empty after delete")
    assert_eq(0, len(data.get("preferred_roles", [])), "preferred_roles should be empty after delete")
    assert_eq(0, len(data.get("experience", [])), "experience should be empty after delete")
    assert_eq(0, len(data.get("education", [])), "education should be empty after delete")
    assert_eq(0, len(data.get("certifications", [])), "certifications should be empty after delete")


def test_09_cv_delete_through_gateway_service() -> None:
    print("[9/9] CV delete through gateway-service")

    status, _ = http_request("DELETE", api_url("/api/v1/profile/cv"), headers=AUTH_HEADERS)
    assert_eq(204, status, "cv delete status code")

    status, payload = http_request("GET", api_url("/api/v1/profile/cv"), headers=AUTH_HEADERS)
    assert_eq(200, status, "cv get after delete status code")
    assert_eq(None, json.loads(payload).get("cv"), "cv should be null after delete")


def run_all_tests() -> None:
    test_01_gateway_health()
    test_02_auth_session_through_gateway_service()
    test_03_profile_read_before_upsert()
    test_04_profile_upsert_and_read()
    test_05_cv_upload_through_gateway_service()
    test_06_database_rows_persisted()
    test_07_profile_validation_rejects_invalid_location_hierarchy()
    test_08_profile_subsections_crud()
    test_09_cv_delete_through_gateway_service()

    print("\nCross-service Python tests passed!")


if __name__ == "__main__":
    run_all_tests()
