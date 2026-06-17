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
