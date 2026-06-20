import pytest
import respx
import httpx

from fastapi.testclient import TestClient
from src.app.main import app
import src.app.main as main_module


@pytest.fixture(autouse=True)
def reset_http_client():
    """Reset the shared HTTP client between tests."""
    main_module._http_client = None
    yield
    if main_module._http_client is not None:
        import asyncio
        asyncio.get_event_loop().run_until_complete(main_module._http_client.aclose())
        main_module._http_client = None


@respx.mock
def test_auth_session_returns_authenticated(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(
            200,
            json={"internal_user_id": "u-123", "created": True},
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/session",
            headers={"Authorization": "Bearer dummy-token"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "authenticated"
    assert data["is_new_user"] is True


def test_auth_session_missing_token():
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/session")
    assert response.status_code == 401


@respx.mock
def test_auth_session_returns_502_when_user_sync_fails(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(500, json={"detail": "boom"})
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/session",
            headers={"Authorization": "Bearer dummy-token"},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "User sync failed"


@respx.mock
def test_get_profile_proxies_to_profile_service(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.get("http://profile-service:8080/internal/users/u-123/profile").mock(
        return_value=httpx.Response(
            200,
            json={"user_id": "u-123", "full_name": "Jane Doe", "email": "test@example.com"},
        )
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/profile",
            headers={"Authorization": "Bearer dummy-token"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "u-123"
    assert data["full_name"] == "Jane Doe"


@respx.mock
def test_get_profile_returns_404_when_not_found(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-456", "created": False})
    )
    respx.get("http://profile-service:8080/internal/users/u-456/profile").mock(
        return_value=httpx.Response(404, json={"detail": "Profile not found"})
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/profile",
            headers={"Authorization": "Bearer dummy-token"},
        )
    assert response.status_code == 404


@respx.mock
def test_get_profile_returns_502_when_profile_service_errors(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.get("http://profile-service:8080/internal/users/u-123/profile").mock(
        return_value=httpx.Response(500, json={"detail": "internal error"})
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/profile",
            headers={"Authorization": "Bearer dummy-token"},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to retrieve profile"


@respx.mock
def test_update_profile_maps_422_validation_detail(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.put("http://profile-service:8080/internal/users/u-123/profile").mock(
        return_value=httpx.Response(422, json={"detail": "city_id is invalid"})
    )

    with TestClient(app) as client:
        response = client.put(
            "/api/v1/profile",
            headers={"Authorization": "Bearer dummy-token"},
            json={"full_name": "User", "city_id": "broken"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "city_id is invalid"


@respx.mock
def test_update_profile_uses_fallback_detail_when_json_is_invalid(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.put("http://profile-service:8080/internal/users/u-123/profile").mock(
        return_value=httpx.Response(422, content=b"not-json")
    )

    with TestClient(app) as client:
        response = client.put(
            "/api/v1/profile",
            headers={"Authorization": "Bearer dummy-token"},
            json={"full_name": "User"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid profile payload"


@respx.mock
def test_get_cv_returns_null_when_internal_cv_not_found(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.get("http://profile-service:8080/internal/users/u-123/cv").mock(
        return_value=httpx.Response(404, json={"detail": "No active CV found"})
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/profile/cv", headers={"Authorization": "Bearer dummy-token"})

    assert response.status_code == 200
    assert response.json() == {"cv": None}


@respx.mock
def test_get_cv_returns_502_when_profile_service_errors(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.get("http://profile-service:8080/internal/users/u-123/cv").mock(
        return_value=httpx.Response(500, json={"detail": "internal error"})
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/profile/cv", headers={"Authorization": "Bearer dummy-token"})

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to retrieve CV"


@respx.mock
def test_delete_cv_returns_204_when_internal_cv_not_found(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.delete("http://profile-service:8080/internal/users/u-123/cv").mock(
        return_value=httpx.Response(404, json={"detail": "No active CV found"})
    )

    with TestClient(app) as client:
        response = client.delete("/api/v1/profile/cv", headers={"Authorization": "Bearer dummy-token"})

    assert response.status_code == 204


@respx.mock
def test_delete_cv_returns_204_when_internal_delete_succeeds(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.delete("http://profile-service:8080/internal/users/u-123/cv").mock(
        return_value=httpx.Response(200, json={"status": "deleted"})
    )

    with TestClient(app) as client:
        response = client.delete("/api/v1/profile/cv", headers={"Authorization": "Bearer dummy-token"})

    assert response.status_code == 204


@respx.mock
def test_add_skill_maps_conflict_from_profile_service(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.post("http://profile-service:8080/internal/users/u-123/skills").mock(
        return_value=httpx.Response(409, json={"detail": "Skill already exists in profile"})
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/profile/skills",
            headers={"Authorization": "Bearer dummy-token"},
            json={"skill_name": "Python"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Skill already exists in profile"


@respx.mock
def test_list_countries_public_proxy(monkeypatch):
    main_module._http_client = None

    respx.get("http://profile-service:8080/internal/locations/countries", params={"limit": "1"}).mock(
        return_value=httpx.Response(200, json={"status": "ok", "countries": [{"code": "AT", "name": "Austria"}]})
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/locations/countries?limit=1")

    assert response.status_code == 200
    assert response.json()["countries"][0]["code"] == "AT"


@respx.mock
def test_list_degree_types_public_proxy(monkeypatch):
    main_module._http_client = None

    respx.get("http://profile-service:8080/internal/catalogs/degree-types", params={"limit": "1"}).mock(
        return_value=httpx.Response(
            200,
            json={"status": "ok", "degree_types": [{"id": "30000000-0000-0000-0000-000000000003", "degree_name": "Bachelor Degree"}]},
        )
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/catalogs/degree-types?limit=1")

    assert response.status_code == 200
    assert response.json()["degree_types"][0]["degree_name"] == "Bachelor Degree"


@respx.mock
def test_list_roles_public_proxy_maps_502_on_failure(monkeypatch):
    main_module._http_client = None

    respx.get("http://profile-service:8080/internal/catalogs/roles", params={"limit": "2"}).mock(
        return_value=httpx.Response(503, json={"detail": "temporarily unavailable"})
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/catalogs/roles?limit=2")

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to retrieve roles catalog"


@respx.mock
def test_update_preferred_role_maps_404_detail(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.put("http://profile-service:8080/internal/users/u-123/preferred-roles/r-404").mock(
        return_value=httpx.Response(404, json={"detail": "Preferred role not found"})
    )

    with TestClient(app) as client:
        response = client.put(
            "/api/v1/profile/preferred-roles/r-404",
            headers={"Authorization": "Bearer dummy-token"},
            json={"role_name": "Backend Engineer"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Preferred role not found"


@respx.mock
def test_delete_experience_maps_404_detail(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.delete("http://profile-service:8080/internal/users/u-123/experience/exp-404").mock(
        return_value=httpx.Response(404, json={"detail": "Experience item not found"})
    )

    with TestClient(app) as client:
        response = client.delete(
            "/api/v1/profile/experience/exp-404",
            headers={"Authorization": "Bearer dummy-token"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Experience item not found"


@respx.mock
def test_update_education_maps_422_detail(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.put("http://profile-service:8080/internal/users/u-123/education/edu-1").mock(
        return_value=httpx.Response(422, json={"detail": "degree_type_id does not exist"})
    )

    with TestClient(app) as client:
        response = client.put(
            "/api/v1/profile/education/edu-1",
            headers={"Authorization": "Bearer dummy-token"},
            json={"degree": "BSc", "institution": "TU", "degree_type_id": "bad"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "degree_type_id does not exist"


@respx.mock
def test_upload_cv_maps_400_detail(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.post("http://profile-service:8080/internal/users/u-123/cv").mock(
        return_value=httpx.Response(400, json={"detail": "Unsupported file extension"})
    )

    files = {"file": ("bad.exe", b"MZ", "application/octet-stream")}

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/profile/cv",
            headers={"Authorization": "Bearer dummy-token"},
            files=files,
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file extension"


@respx.mock
def test_upload_cv_returns_202_on_success(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.post("http://profile-service:8080/internal/users/u-123/cv").mock(
        return_value=httpx.Response(200, json={"status": "accepted", "cv_upload_record": {"id": "cv-1"}})
    )

    files = {"file": ("cv.txt", b"Curriculum Vitae\nSkills: Python", "text/plain")}

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/profile/cv",
            headers={"Authorization": "Bearer dummy-token"},
            files=files,
        )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


@respx.mock
def test_upload_cv_returns_502_on_unexpected_profile_error(monkeypatch):
    main_module._http_client = None

    respx.post("http://profile-service:8080/internal/users/sync-from-jwt").mock(
        return_value=httpx.Response(200, json={"internal_user_id": "u-123", "created": False})
    )
    respx.post("http://profile-service:8080/internal/users/u-123/cv").mock(
        return_value=httpx.Response(500, json={"detail": "storage unavailable"})
    )

    files = {"file": ("cv.txt", b"Curriculum Vitae\nSkills: Python", "text/plain")}

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/profile/cv",
            headers={"Authorization": "Bearer dummy-token"},
            files=files,
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "CV upload failed"


@respx.mock
def test_list_regions_forwards_country_code_and_limit(monkeypatch):
    main_module._http_client = None

    respx.get(
        "http://profile-service:8080/internal/locations/regions",
        params={"limit": "3", "country_code": "AT"},
    ).mock(
        return_value=httpx.Response(
            200,
            json={"status": "ok", "regions": [{"id": "00000003-0000-0000-0000-000000000003", "name": "Vienna"}]},
        )
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/locations/regions?country_code=AT&limit=3")

    assert response.status_code == 200
    assert response.json()["regions"][0]["name"] == "Vienna"


@respx.mock
def test_list_regions_maps_502_on_failure(monkeypatch):
    main_module._http_client = None

    respx.get(
        "http://profile-service:8080/internal/locations/regions",
        params={"limit": "5"},
    ).mock(return_value=httpx.Response(500, json={"detail": "backend down"}))

    with TestClient(app) as client:
        response = client.get("/api/v1/locations/regions?limit=5")

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to retrieve regions"


@respx.mock
def test_list_skills_catalog_forwards_filters(monkeypatch):
    main_module._http_client = None

    respx.get(
        "http://profile-service:8080/internal/catalogs/skills",
        params={"limit": "2", "q": "python", "category": "backend"},
    ).mock(
        return_value=httpx.Response(
            200,
            json={"status": "ok", "skills": [{"id": "10000000-0000-0000-0000-000000000001", "skill_name": "Python"}]},
        )
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/catalogs/skills?q=python&category=backend&limit=2")

    assert response.status_code == 200
    assert response.json()["skills"][0]["skill_name"] == "Python"


@respx.mock
def test_list_cities_forwards_all_filters(monkeypatch):
    main_module._http_client = None

    respx.get(
        "http://profile-service:8080/internal/locations/cities",
        params={
            "limit": "4",
            "country_code": "AT",
            "region_id": "00000003-0000-0000-0000-000000000003",
        },
    ).mock(
        return_value=httpx.Response(
            200,
            json={"status": "ok", "cities": [{"id": "10000003-0000-0000-0000-000000000003", "name": "Vienna"}]},
        )
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/locations/cities?country_code=AT&region_id=00000003-0000-0000-0000-000000000003&limit=4"
        )

    assert response.status_code == 200
    assert response.json()["cities"][0]["name"] == "Vienna"


@respx.mock
def test_list_skills_catalog_maps_502_on_failure(monkeypatch):
    main_module._http_client = None

    respx.get(
        "http://profile-service:8080/internal/catalogs/skills",
        params={"limit": "10"},
    ).mock(return_value=httpx.Response(502, json={"detail": "upstream failed"}))

    with TestClient(app) as client:
        response = client.get("/api/v1/catalogs/skills?limit=10")

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to retrieve skills catalog"
