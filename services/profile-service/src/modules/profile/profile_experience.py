from __future__ import annotations

import json
from typing import Any
from uuid import uuid4


class ProfileExperienceStoreMixin:
    def add_experience(self, user_id: str, data: dict) -> dict[str, Any]:
        position = self._normalize_required_text(data.get("position"), "position")
        company = self._normalize_required_text(data.get("company"), "company")
        start_date = self._normalize_optional_date(data.get("start_date"), "start_date")
        if start_date is None:
            raise ValueError("start_date is required")
        end_date = self._normalize_optional_date(data.get("end_date"), "end_date")
        self._ensure_date_order(start_date, end_date, "start_date", "end_date")
        is_current = bool(data.get("is_current", False))
        responsibilities = data.get("responsibilities")
        if responsibilities is None:
            responsibilities = []
        if not isinstance(responsibilities, list):
            raise ValueError("responsibilities must be a list")

        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_profile_exists(cur, user_id)
                cur.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM profile_experience WHERE profile_id = %s",
                    (user_id,),
                )
                next_sort_order = cur.fetchone()[0]
                experience_id = str(uuid4())
                cur.execute(
                    """
                    INSERT INTO profile_experience (
                        id, profile_id, position, company, start_date, end_date, is_current, responsibilities, sort_order
                    )
                    VALUES (%s, %s, %s, %s, %s::date, %s::date, %s, %s::jsonb, %s)
                    """,
                    (
                        experience_id,
                        user_id,
                        position,
                        company,
                        start_date,
                        end_date,
                        is_current,
                        json.dumps(responsibilities),
                        next_sort_order,
                    ),
                )
                return {
                    "id": experience_id,
                    "position": position,
                    "company": company,
                    "start_date": start_date,
                    "end_date": end_date,
                    "is_current": is_current,
                    "responsibilities": responsibilities,
                }

    def update_experience(self, user_id: str, experience_id: str, data: dict) -> dict[str, Any]:
        position = self._normalize_required_text(data.get("position"), "position")
        company = self._normalize_required_text(data.get("company"), "company")
        start_date = self._normalize_optional_date(data.get("start_date"), "start_date")
        if start_date is None:
            raise ValueError("start_date is required")
        end_date = self._normalize_optional_date(data.get("end_date"), "end_date")
        self._ensure_date_order(start_date, end_date, "start_date", "end_date")
        is_current = bool(data.get("is_current", False))
        responsibilities = data.get("responsibilities")
        if responsibilities is None:
            responsibilities = []
        if not isinstance(responsibilities, list):
            raise ValueError("responsibilities must be a list")

        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_profile_exists(cur, user_id)
                cur.execute(
                    """
                    UPDATE profile_experience
                    SET position = %s,
                        company = %s,
                        start_date = %s::date,
                        end_date = %s::date,
                        is_current = %s,
                        responsibilities = %s::jsonb,
                        updated_at = NOW()
                    WHERE profile_id = %s AND id = %s
                    RETURNING id
                    """,
                    (
                        position,
                        company,
                        start_date,
                        end_date,
                        is_current,
                        json.dumps(responsibilities),
                        user_id,
                        experience_id,
                    ),
                )
                if cur.fetchone() is None:
                    raise ValueError("Experience item not found")
                return {
                    "id": experience_id,
                    "position": position,
                    "company": company,
                    "start_date": start_date,
                    "end_date": end_date,
                    "is_current": is_current,
                    "responsibilities": responsibilities,
                }

    def delete_experience(self, user_id: str, experience_id: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_profile_exists(cur, user_id)
                cur.execute(
                    "DELETE FROM profile_experience WHERE profile_id = %s AND id = %s RETURNING id",
                    (user_id, experience_id),
                )
                if cur.fetchone() is None:
                    raise ValueError("Experience item not found")
