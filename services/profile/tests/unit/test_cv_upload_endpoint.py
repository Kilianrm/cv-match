from fastapi.testclient import TestClient

from src.app.main import app
from src.app import main as main_module


client = TestClient(app)


def test_upload_cv_accepts_valid_text_cv(monkeypatch):
    captured = {}

    def fake_upload_bytes(object_key: str, content: bytes, content_type: str | None):
        captured["object_key"] = object_key
        captured["content"] = content
        captured["content_type"] = content_type

    def fake_register_cv_upload(
        user_id: str,
        original_filename: str,
        storage_key: str,
        content_type: str,
        parse_status: str,
    ):
        captured["register_user_id"] = user_id
        captured["register_filename"] = original_filename
        captured["register_storage_key"] = storage_key
        captured["register_content_type"] = content_type
        captured["register_parse_status"] = parse_status
        return {
            "id": "cv-1",
            "uploaded_at": "2026-06-20T00:00:00+00:00",
            "parse_status": "pending",
            "is_active": True,
            "storage_key": storage_key,
            "original_filename": original_filename,
            "content_type": content_type,
        }

    monkeypatch.setattr(main_module.storage, "upload_bytes", fake_upload_bytes)
    monkeypatch.setattr(main_module.profile_store, "register_cv_upload", fake_register_cv_upload)

    files = {
        "file": (
            "cv.txt",
            b"Curriculum Vitae\nExperience: 3 years\nSkills: Python",
            "text/plain",
        )
    }

    response = client.post("/internal/users/u-1/cv", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["user_id"] == "u-1"
    assert body["object_key"] == "cv/u-1/cv.txt"
    assert body["cv_upload_record"]["id"] == "cv-1"
    assert captured["object_key"] == "cv/u-1/cv.txt"
    assert captured["register_user_id"] == "u-1"
    assert captured["register_filename"] == "cv.txt"
    assert captured["register_storage_key"] == "cv/u-1/cv.txt"
    assert captured["register_parse_status"] == "pending"


def test_upload_cv_rejects_text_that_is_not_cv(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("upload_bytes should not be called for invalid CV")

    monkeypatch.setattr(main_module.storage, "upload_bytes", fail_if_called)

    files = {
        "file": (
            "notes.txt",
            b"hello world",
            "text/plain",
        )
    }

    response = client.post("/internal/users/u-2/cv", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "Text file content does not look like a CV"


def test_upload_cv_rejects_unsupported_extension(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("upload_bytes should not be called for invalid file type")

    monkeypatch.setattr(main_module.storage, "upload_bytes", fail_if_called)

    files = {
        "file": (
            "malware.exe",
            b"MZ...",
            "application/octet-stream",
        )
    }

    response = client.post("/internal/users/u-3/cv", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file extension"
