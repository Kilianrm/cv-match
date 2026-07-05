from __future__ import annotations

from typing import Any
from uuid import uuid4


class ProfileSkillsStoreMixin:
    def _get_skill_by_label(self, cur, label: str) -> tuple[str, str] | None:
        normalized_skill = self._normalize_token(label)
        cur.execute(
            "SELECT id, skill_name FROM skills WHERE normalized_skill = %s",
            (normalized_skill,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return str(row[0]), row[1]

    def add_skill(self, user_id: str, skill_label: str, proficiency_level: str | None = None) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_profile_exists(cur, user_id)
                label = self._normalize_required_text(skill_label, "skill_label")
                skill_row = self._get_skill_by_label(cur, label)
                if skill_row is None:
                    raise ValueError("Skill is not in catalog")
                skill_id, catalog_label = skill_row

                cur.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM profile_skills WHERE profile_id = %s",
                    (user_id,),
                )
                next_sort_order = cur.fetchone()[0]

                relation_id = str(uuid4())
                try:
                    cur.execute(
                        """
                        INSERT INTO profile_skills (id, profile_id, skill_id, proficiency_level, sort_order)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (relation_id, user_id, skill_id, proficiency_level, next_sort_order),
                    )
                except Exception as exc:
                    if "profile_skills_profile_id_skill_id_key" in str(exc):
                        raise ValueError("Skill already exists in profile") from exc
                    raise

                return {
                    "id": relation_id,
                    "skill_id": skill_id,
                    "label": catalog_label,
                    "proficiency_level": proficiency_level,
                }

    def remove_skill(self, user_id: str, skill_id: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_profile_exists(cur, user_id)
                cur.execute(
                    "DELETE FROM profile_skills WHERE profile_id = %s AND skill_id = %s RETURNING id",
                    (user_id, skill_id),
                )
                if cur.fetchone() is None:
                    raise ValueError("Skill not found in profile")
