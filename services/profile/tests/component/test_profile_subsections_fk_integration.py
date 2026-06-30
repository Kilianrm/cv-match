import uuid

from fastapi.testclient import TestClient

from src.app.main import app


client = TestClient(app)


def _create_user_and_profile() -> str:
    payload = {
        "issuer": f"https://issuer.example/{uuid.uuid4()}",
        "sub": str(uuid.uuid4()),
        "email": f"u-{uuid.uuid4()}@example.com",
    }
    response = client.post("/internal/users/sync-from-jwt", json=payload)
    assert response.status_code == 200
    user_id = response.json()["internal_user_id"]

    profile_response = client.post(
        f"/internal/users/{user_id}/profile",
        json={"full_name": "Integration Test User"},
    )
    assert profile_response.status_code == 200

    return user_id


def test_add_preferred_role_with_role_id_persists_in_profile() -> None:
    user_id = _create_user_and_profile()
    known_role_id = "20000000-0000-0000-0000-000000000002"

    create_response = client.post(
        f"/internal/users/{user_id}/preferred-roles",
        json={"role_name": "Backend Engineer", "role_id": known_role_id},
    )
    assert create_response.status_code == 200
    item = create_response.json()["item"]
    assert item["role_id"] == known_role_id

    profile_response = client.get(f"/internal/users/{user_id}/profile")
    assert profile_response.status_code == 200
    preferred_roles = profile_response.json().get("preferred_roles", [])
    assert len(preferred_roles) == 1
    assert preferred_roles[0]["role_id"] == known_role_id


def test_add_preferred_role_rejects_invalid_role_id() -> None:
    user_id = _create_user_and_profile()

    response = client.post(
        f"/internal/users/{user_id}/preferred-roles",
        json={"role_name": "Backend Engineer", "role_id": "not-a-uuid"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "role_id must be a valid UUID"


def test_add_education_with_degree_type_id_persists_in_profile() -> None:
    user_id = _create_user_and_profile()
    known_degree_type_id = "30000000-0000-0000-0000-000000000003"

    create_response = client.post(
        f"/internal/users/{user_id}/education",
        json={
            "degree_type_id": known_degree_type_id,
            "degree": "BSc Computer Science",
            "institution": "TU Vienna",
            "start_date": "2018-09-01",
            "end_date": "2021-06-30",
            "status": "completed",
        },
    )
    assert create_response.status_code == 200
    item = create_response.json()["item"]
    assert item["degree_type_id"] == known_degree_type_id

    profile_response = client.get(f"/internal/users/{user_id}/profile")
    assert profile_response.status_code == 200
    education = profile_response.json().get("education", [])
    assert len(education) == 1
    assert education[0]["degree_type_id"] == known_degree_type_id


def test_add_education_rejects_unknown_degree_type_id() -> None:
    user_id = _create_user_and_profile()

    response = client.post(
        f"/internal/users/{user_id}/education",
        json={
            "degree_type_id": "30000000-0000-0000-0000-00000000ffff",
            "degree": "BSc Computer Science",
            "institution": "TU Vienna",
            "start_date": "2018-09-01",
            "end_date": "2021-06-30",
            "status": "completed",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "degree_type_id does not exist"
