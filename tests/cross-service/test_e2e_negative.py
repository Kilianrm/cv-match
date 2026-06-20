#!/usr/bin/env python3
"""Negative cross-service end-to-end checks for local MVP.

This suite complements test_e2e.py by focusing on critical failure and
validation scenarios without repeating the main happy path coverage.
"""

from __future__ import annotations

import json

from test_e2e import assert_eq, http_request, wait_for_gateway


AUTH_HEADERS = {"Authorization": "Bearer local-dev-token"}


def test_01_gateway_health_for_negative_suite() -> None:
    print("[neg 1/6] Waiting for gateway-service health")
    wait_for_gateway()


def test_02_auth_session_rejects_missing_authorization() -> None:
    print("[neg 2/6] auth/session rejects missing authorization")
    status, payload = http_request("POST", "http://localhost:8000/api/v1/auth/session")
    assert_eq(401, status, "auth/session missing auth status code")
    assert_eq("Missing or invalid Authorization header", json.loads(payload).get("detail"), "auth/session missing auth detail")


def test_03_profile_read_rejects_missing_authorization() -> None:
    print("[neg 3/6] profile read rejects missing authorization")
    status, payload = http_request("GET", "http://localhost:8000/api/v1/profile")
    assert_eq(401, status, "profile read missing auth status code")
    assert_eq("Missing or invalid Authorization header", json.loads(payload).get("detail"), "profile read missing auth detail")


def test_04_profile_update_rejects_invalid_location_hierarchy() -> None:
    print("[neg 4/6] profile update rejects invalid location hierarchy")
    invalid_body = json.dumps(
        {
            "full_name": "Negative Test User",
            "headline": "QA Engineer",
            "city_id": "10000003-0000-0000-0000-000000000003",
        }
    ).encode("utf-8")

    status, payload = http_request(
        "PUT",
        "http://localhost:8000/api/v1/profile",
        body=invalid_body,
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
    )
    assert_eq(422, status, "invalid location hierarchy status code")
    assert_eq(
        "region_id is required when city_id is provided",
        json.loads(payload).get("detail"),
        "invalid location hierarchy detail",
    )


def test_05_cv_upload_rejects_invalid_extension() -> None:
    print("[neg 5/6] cv upload rejects invalid extension")
    boundary = "----cvmatchboundaryNegative7MA4YWxkTrZu0gW"
    multipart = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"malware.exe\"\r\n"
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + b"MZ..." + f"\r\n--{boundary}--\r\n".encode("utf-8")

    status, payload = http_request(
        "POST",
        "http://localhost:8000/api/v1/profile/cv",
        body=multipart,
        headers={
            **AUTH_HEADERS,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    assert_eq(400, status, "invalid cv upload status code")
    assert_eq("Unsupported file extension", json.loads(payload).get("detail"), "invalid cv upload detail")


def test_06_public_locations_endpoint_is_available() -> None:
    print("[neg 6/6] public locations endpoint remains available without auth")
    status, payload = http_request("GET", "http://localhost:8000/api/v1/locations/countries?limit=2")
    assert_eq(200, status, "public countries status code")
    data = json.loads(payload)
    countries = data.get("countries", [])
    if not isinstance(countries, list) or len(countries) == 0:
        raise AssertionError("expected non-empty countries list from public endpoint")


def run_all_tests() -> None:
    test_01_gateway_health_for_negative_suite()
    test_02_auth_session_rejects_missing_authorization()
    test_03_profile_read_rejects_missing_authorization()
    test_04_profile_update_rejects_invalid_location_hierarchy()
    test_05_cv_upload_rejects_invalid_extension()
    test_06_public_locations_endpoint_is_available()

    print("\nCross-service negative Python tests passed!")


if __name__ == "__main__":
    run_all_tests()