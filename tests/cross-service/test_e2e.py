#!/usr/bin/env python3
"""Cross-service end-to-end checks for local MVP.

This module is pytest-compatible (test_* functions) and also supports
direct execution via `python3 test_e2e.py` when pytest is unavailable.
"""

from __future__ import annotations

import json
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


def wait_for_gateway(timeout_seconds: int = 60) -> None:
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            status, payload = http_request("GET", "http://localhost:8000/health")
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
            "http://localhost:8000/api/v1/auth/session",
            headers=AUTH_HEADERS,
        )
        last_status = status
        last_payload = payload
        if status == 200:
            return status, payload
        time.sleep(1)
    raise TimeoutError(f"auth/session did not become ready in time (last status={last_status}, body={last_payload})")


def psql_scalar(query: str) -> str:
    cmd = [
        "docker",
        "exec",
        "-i",
        "profile-postgres",
        "psql",
        "-U",
        "profile_user",
        "-d",
        "profile_db",
        "-tA",
        "-c",
        query,
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


AUTH_HEADERS = {"Authorization": "Bearer local-dev-token"}


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
    status, _ = http_request("GET", "http://localhost:8000/api/v1/profile", headers=AUTH_HEADERS)
    if status not in (200, 404):
        raise AssertionError(f"initial profile read status code: expected 200 or 404, got {status}")


def test_04_profile_upsert_and_read() -> None:
    print("[4/6] profile upsert through gateway-service")
    update_body = json.dumps(
        {
            "full_name": "Local Test User",
            "headline": "QA Engineer",
            "location": "Buenos Aires",
        }
    ).encode("utf-8")
    status, payload = http_request(
        "PUT",
        "http://localhost:8000/api/v1/profile",
        body=update_body,
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
    )
    assert_eq(200, status, "profile update status code")
    data = json.loads(payload)
    assert_eq("accepted", data.get("status"), "profile update payload status")

    print("[5/6] profile read after upsert")
    status, payload = http_request("GET", "http://localhost:8000/api/v1/profile", headers=AUTH_HEADERS)
    assert_eq(200, status, "profile read after upsert status code")
    data = json.loads(payload)
    assert_eq("Local Test User", data.get("full_name"), "profile full_name")


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
        "http://localhost:8000/api/v1/cv/upload",
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
    print("Verifying users row exists in PostgreSQL")
    user_count = psql_scalar("SELECT count(*) FROM users WHERE cognito_sub='local-user-sub';")
    assert_eq("1", user_count, "users row count")

    print("Verifying upserted profile values are persisted in PostgreSQL")
    profile_row = psql_scalar(
        """
        SELECT p.full_name || '|' || COALESCE(p.headline, '') || '|' || COALESCE(p.location, '')
        FROM profiles p
        JOIN users u ON u.id = p.user_id
        WHERE u.cognito_sub = 'local-user-sub'
        LIMIT 1;
        """
    )
    if not profile_row:
        raise AssertionError("expected profile row for cognito_sub=local-user-sub")

    parts = profile_row.split("|", 2)
    if len(parts) != 3:
        raise AssertionError(f"unexpected profile row shape: {profile_row}")

    assert_eq("Local Test User", parts[0], "stored profile full_name")
    assert_eq("QA Engineer", parts[1], "stored profile headline")
    assert_eq("Buenos Aires", parts[2], "stored profile location")


def run_all_tests() -> None:
    test_01_gateway_health()
    test_02_auth_session_through_gateway_service()
    test_03_profile_read_before_upsert()
    test_04_profile_upsert_and_read()
    test_05_cv_upload_through_gateway_service()
    test_06_database_rows_persisted()

    print("\nCross-service Python tests passed!")


if __name__ == "__main__":
    run_all_tests()
