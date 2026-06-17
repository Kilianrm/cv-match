import uuid

from fastapi.testclient import TestClient

from src.app.main import app
from src.app import main as main_module
from src.modules.users.users_store import UsersStore
from src.shared.config import settings


client = TestClient(app)


def test_sync_from_jwt_is_idempotent_for_same_issuer_sub():
    main_module.users_store = UsersStore(settings.database_url)
    unique_issuer = f"https://cognito-idp.us-east-1.amazonaws.com/us-east-1_{uuid.uuid4()}"
    unique_sub = str(uuid.uuid4())

    payload = {
        "issuer": unique_issuer,
        "sub": unique_sub,
        "email": "user@example.com",
    }

    first_response = client.post("/internal/users/sync-from-jwt", json=payload)
    second_response = client.post("/internal/users/sync-from-jwt", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_body = first_response.json()
    second_body = second_response.json()

    assert first_body["created"] is True
    assert second_body["created"] is False
    assert first_body["internal_user_id"] == second_body["internal_user_id"]


def test_sync_from_jwt_creates_distinct_internal_ids_for_different_subjects():
    main_module.users_store = UsersStore(settings.database_url)

    issuer = f"https://cognito-idp.us-east-1.amazonaws.com/us-east-1_{uuid.uuid4()}"

    response_a = client.post(
        "/internal/users/sync-from-jwt",
        json={
            "issuer": issuer,
            "sub": "sub-A",
            "email": "a@example.com",
        },
    )
    response_b = client.post(
        "/internal/users/sync-from-jwt",
        json={
            "issuer": issuer,
            "sub": "sub-B",
            "email": "b@example.com",
        },
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    assert response_a.json()["internal_user_id"] != response_b.json()["internal_user_id"]
