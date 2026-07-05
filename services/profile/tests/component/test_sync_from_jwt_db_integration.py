import time
import uuid

from fastapi.testclient import TestClient
from psycopg import connect

from src.app.main import app
from src.shared.config import settings


client = TestClient(app)


def _fetch_user_by_sub(cognito_sub: str):
    with connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, cognito_sub, email, email_verified, status,
                       last_synced_from_cognito_at, created_at, updated_at
                FROM users
                WHERE cognito_sub = %s
                """,
                (cognito_sub,),
            )
            return cur.fetchone()


def test_sync_from_jwt_persists_user_row_with_expected_defaults():
    unique_sub = str(uuid.uuid4())
    payload = {
        "issuer": f"https://issuer.example/{uuid.uuid4()}",
        "sub": unique_sub,
        "email": "sync-defaults@example.com",
    }

    response = client.post("/internal/users/sync-from-jwt", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["created"] is True

    row = _fetch_user_by_sub(unique_sub)
    assert row is not None
    assert str(row[0]) == body["internal_user_id"]
    assert row[1] == unique_sub
    assert row[2] == "sync-defaults@example.com"
    assert row[3] is False
    assert row[4] == "active"
    assert row[5] is not None
    assert row[6] is not None
    assert row[7] is not None


def test_sync_from_jwt_updates_email_and_sync_timestamp_on_repeat_call():
    unique_sub = str(uuid.uuid4())
    issuer = f"https://issuer.example/{uuid.uuid4()}"

    first_response = client.post(
        "/internal/users/sync-from-jwt",
        json={
            "issuer": issuer,
            "sub": unique_sub,
            "email": "before-update@example.com",
        },
    )
    assert first_response.status_code == 200
    first_user_id = first_response.json()["internal_user_id"]

    first_row = _fetch_user_by_sub(unique_sub)
    assert first_row is not None
    first_synced_at = first_row[5]

    time.sleep(0.01)

    second_response = client.post(
        "/internal/users/sync-from-jwt",
        json={
            "issuer": issuer,
            "sub": unique_sub,
            "email": "after-update@example.com",
        },
    )
    assert second_response.status_code == 200
    assert second_response.json()["created"] is False
    assert second_response.json()["internal_user_id"] == first_user_id

    second_row = _fetch_user_by_sub(unique_sub)
    assert second_row is not None
    assert second_row[2] == "after-update@example.com"
    assert second_row[5] is not None
    assert second_row[5] >= first_synced_at
