import uuid

from fastapi.testclient import TestClient

from src.app.main import app
from src.app import main as main_module
from src.modules.users.users_store import UsersStore
from src.shared.config import settings


client = TestClient(app)


def test_sync_from_jwt_rejects_missing_required_sub_field():
    response = client.post(
        "/internal/users/sync-from-jwt",
        json={
            "issuer": "https://issuer.example/test",
            "email": "user@example.com",
        },
    )

    assert response.status_code == 422


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


def test_sync_from_jwt_logs_safe_user_created_field(capsys):
    main_module.users_store = UsersStore(settings.database_url)

    issuer = f"https://cognito-idp.us-east-1.amazonaws.com/us-east-1_{uuid.uuid4()}"

    response = client.post(
        "/internal/users/sync-from-jwt",
        json={
            "issuer": issuer,
            "sub": "safe-log-subject",
            "email": "safe-log@example.com",
        },
    )

    assert response.status_code == 200

    stderr = capsys.readouterr().err
    assert '"event": "user_sync"' in stderr
    assert '"user_created": true' in stderr
