from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.modules.profile.profile_certifications import ProfileCertificationsStoreMixin
from src.modules.profile.profile_cv_upload import ProfileCvUploadStoreMixin
from src.modules.profile.profile_experience import ProfileExperienceStoreMixin
from src.modules.profile.profile_shared import ProfileSharedMixin
from src.modules.profile.profile_skills import ProfileSkillsStoreMixin


class ScriptedCursor:
    def __init__(self, fetchone_results: list[object], raise_on_execute: dict[int, Exception] | None = None) -> None:
        self._fetchone_results = list(fetchone_results)
        self._raise_on_execute = raise_on_execute or {}
        self.execute_count = 0
        self.executed: list[tuple[str, object]] = []

    def execute(self, sql: str, params: object = None) -> None:
        self.execute_count += 1
        normalized_sql = " ".join(sql.split())
        self.executed.append((normalized_sql, params))
        if self.execute_count in self._raise_on_execute:
            raise self._raise_on_execute[self.execute_count]

    def fetchone(self):
        if not self._fetchone_results:
            return None
        return self._fetchone_results.pop(0)


class CursorContext:
    def __init__(self, cursor: ScriptedCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> ScriptedCursor:
        return self._cursor

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class ConnectionContext:
    def __init__(self, cursor: ScriptedCursor) -> None:
        self._cursor = cursor

    def cursor(self) -> CursorContext:
        return CursorContext(self._cursor)

    def __enter__(self) -> "ConnectionContext":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class DummyStore(
    ProfileSharedMixin,
    ProfileCvUploadStoreMixin,
    ProfileSkillsStoreMixin,
    ProfileExperienceStoreMixin,
    ProfileCertificationsStoreMixin,
):
    def __init__(self, cursor: ScriptedCursor) -> None:
        self._cursor = cursor

    def _connect(self) -> ConnectionContext:
        return ConnectionContext(self._cursor)


def test_register_cv_upload_returns_record_and_enforces_user_exists() -> None:
    uploaded_at = datetime(2026, 6, 20, 10, 30, tzinfo=timezone.utc)
    cursor = ScriptedCursor(
        fetchone_results=[
            (1,),
            ("cv-123", uploaded_at, "pending", True),
        ]
    )
    store = DummyStore(cursor)

    result = store.register_cv_upload("u-1", "cv.pdf", "cv/u-1/cv.pdf", "application/pdf")

    assert result["id"] == "cv-123"
    assert result["uploaded_at"] == uploaded_at.isoformat()
    assert result["parse_status"] == "pending"
    assert result["is_active"] is True


def test_register_cv_upload_raises_when_user_not_found() -> None:
    cursor = ScriptedCursor(fetchone_results=[None])
    store = DummyStore(cursor)

    with pytest.raises(ValueError, match="User not found"):
        store.register_cv_upload("u-404", "cv.pdf", "cv/u-404/cv.pdf", "application/pdf")


def test_get_active_cv_returns_none_when_no_active_record() -> None:
    cursor = ScriptedCursor(fetchone_results=[None])
    store = DummyStore(cursor)

    assert store.get_active_cv("u-1") is None


def test_deactivate_active_cv_returns_false_when_no_cv() -> None:
    cursor = ScriptedCursor(fetchone_results=[(1,), None])
    store = DummyStore(cursor)

    assert store.deactivate_active_cv("u-1") is False


def test_get_skill_by_label_normalizes_token() -> None:
    cursor = ScriptedCursor(fetchone_results=[("skill-1", "Python")])
    store = DummyStore(cursor)

    skill = store._get_skill_by_label(cursor, "  PyThOn   Advanced  ")

    assert skill == ("skill-1", "Python")
    assert cursor.executed[0][1] == ("python advanced",)


def test_add_skill_returns_catalog_skill() -> None:
    cursor = ScriptedCursor(fetchone_results=[(1,), ("skill-1", "Python"), (2,)])
    store = DummyStore(cursor)

    result = store.add_skill("u-1", "Python", "advanced")

    assert result["skill_id"] == "skill-1"
    assert result["label"] == "Python"
    assert result["proficiency_level"] == "advanced"


def test_add_skill_rejects_duplicate_relation() -> None:
    cursor = ScriptedCursor(
        fetchone_results=[(1,), ("skill-1", "Python"), (0,)],
        raise_on_execute={4: Exception("profile_skills_profile_id_skill_id_key")},
    )
    store = DummyStore(cursor)

    with pytest.raises(ValueError, match="Skill already exists in profile"):
        store.add_skill("u-1", "Python")


def test_remove_skill_raises_when_missing() -> None:
    cursor = ScriptedCursor(fetchone_results=[(1,), None])
    store = DummyStore(cursor)

    with pytest.raises(ValueError, match="Skill not found in profile"):
        store.remove_skill("u-1", "skill-404")


def test_add_experience_rejects_non_list_responsibilities() -> None:
    cursor = ScriptedCursor(fetchone_results=[])
    store = DummyStore(cursor)

    with pytest.raises(ValueError, match="responsibilities must be a list"):
        store.add_experience(
            "u-1",
            {
                "position": "Backend Engineer",
                "company": "Acme",
                "start_date": "2022-01-01",
                "responsibilities": "not-a-list",
            },
        )


def test_add_experience_defaults_responsibilities_to_empty_list() -> None:
    cursor = ScriptedCursor(fetchone_results=[(1,), (3,)])
    store = DummyStore(cursor)

    result = store.add_experience(
        "u-1",
        {
            "position": "Backend Engineer",
            "company": "Acme",
            "start_date": "2022-01-01",
            "end_date": None,
            "is_current": True,
        },
    )

    assert result["responsibilities"] == []
    assert result["is_current"] is True


def test_update_experience_raises_when_item_missing() -> None:
    cursor = ScriptedCursor(fetchone_results=[(1,), None])
    store = DummyStore(cursor)

    with pytest.raises(ValueError, match="Experience item not found"):
        store.update_experience(
            "u-1",
            "exp-1",
            {
                "position": "Backend Engineer",
                "company": "Acme",
                "start_date": "2022-01-01",
                "end_date": None,
                "is_current": False,
                "responsibilities": [],
            },
        )


def test_delete_experience_raises_when_item_missing() -> None:
    cursor = ScriptedCursor(fetchone_results=[(1,), None])
    store = DummyStore(cursor)

    with pytest.raises(ValueError, match="Experience item not found"):
        store.delete_experience("u-1", "exp-404")


def test_add_certification_and_update_not_found_path() -> None:
    add_cursor = ScriptedCursor(fetchone_results=[(1,)])
    add_store = DummyStore(add_cursor)

    created = add_store.add_certification(
        "u-1",
        {
            "name": "AWS Developer",
            "issuer": "Amazon",
            "issued_at": "2024-01-15",
            "expires_at": "2027-01-15",
        },
    )
    assert created["name"] == "AWS Developer"

    update_cursor = ScriptedCursor(fetchone_results=[(1,), None])
    update_store = DummyStore(update_cursor)

    with pytest.raises(ValueError, match="Certification item not found"):
        update_store.update_certification(
            "u-1",
            "cert-1",
            {
                "name": "AWS Developer",
                "issuer": "Amazon",
                "issued_at": "2024-01-15",
                "expires_at": "2027-01-15",
            },
        )


def test_delete_certification_raises_when_item_missing() -> None:
    cursor = ScriptedCursor(fetchone_results=[(1,), None])
    store = DummyStore(cursor)

    with pytest.raises(ValueError, match="Certification item not found"):
        store.delete_certification("u-1", "cert-404")
