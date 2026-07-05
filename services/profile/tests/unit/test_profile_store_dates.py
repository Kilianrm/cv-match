import pytest

from src.modules.profile.profile_store import ProfileStore


def build_store_without_db(monkeypatch: pytest.MonkeyPatch) -> ProfileStore:
    monkeypatch.setattr(ProfileStore, "_initialize_schema", lambda self: None)
    return ProfileStore("postgresql://ignored")


def test_add_experience_rejects_invalid_start_date_before_db_access(monkeypatch: pytest.MonkeyPatch) -> None:
    store = build_store_without_db(monkeypatch)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("database connection should not be used for invalid dates")

    monkeypatch.setattr(store, "_connect", fail_if_called)

    with pytest.raises(ValueError, match="start_date must be a valid date in YYYY-MM-DD format"):
        store.add_experience(
            "user-1",
            {
                "position": "Backend Engineer",
                "company": "Acme",
                "start_date": "2022-13-01",
                "end_date": None,
                "is_current": True,
                "responsibilities": [],
            },
        )


def test_add_education_rejects_reversed_date_range_before_db_access(monkeypatch: pytest.MonkeyPatch) -> None:
    store = build_store_without_db(monkeypatch)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("database connection should not be used for invalid dates")

    monkeypatch.setattr(store, "_connect", fail_if_called)

    with pytest.raises(ValueError, match="end_date cannot be earlier than start_date"):
        store.add_education(
            "user-1",
            {
                "degree": "BSc Computer Science",
                "institution": "TU Vienna",
                "start_date": "2021-09-01",
                "end_date": "2020-06-30",
                "status": "completed",
            },
        )