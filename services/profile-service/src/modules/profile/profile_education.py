from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4


class ProfileEducationStoreMixin:
    def _normalize_optional_degree_type_id(self, cur, degree_type_id: str | None) -> str | None:
        normalized = self._normalize_optional_text(degree_type_id)
        if not normalized:
            return None

        try:
            normalized = str(UUID(normalized))
        except ValueError as exc:
            raise ValueError("degree_type_id must be a valid UUID") from exc

        cur.execute("SELECT 1 FROM degree_types WHERE id = %s", (normalized,))
        if cur.fetchone() is None:
            raise ValueError("degree_type_id does not exist")

        return normalized

    def add_education(self, user_id: str, data: dict) -> dict[str, Any]:
        degree = self._normalize_required_text(data.get("degree"), "degree")
        institution = self._normalize_required_text(data.get("institution"), "institution")
        start_date = self._normalize_optional_date(data.get("start_date"), "start_date")
        end_date = self._normalize_optional_date(data.get("end_date"), "end_date")
        self._ensure_date_order(start_date, end_date, "start_date", "end_date")
        status = self._normalize_optional_text(data.get("status"))

        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_profile_exists(cur, user_id)
                normalized_degree_type_id = self._normalize_optional_degree_type_id(cur, data.get("degree_type_id"))
                cur.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM profile_education WHERE profile_id = %s",
                    (user_id,),
                )
                next_sort_order = cur.fetchone()[0]
                education_id = str(uuid4())
                cur.execute(
                    """
                    INSERT INTO profile_education (id, profile_id, degree_type_id, degree, institution, start_date, end_date, status, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s::date, %s::date, %s, %s)
                    """,
                    (
                        education_id,
                        user_id,
                        normalized_degree_type_id,
                        degree,
                        institution,
                        start_date,
                        end_date,
                        status,
                        next_sort_order,
                    ),
                )
                return {
                    "id": education_id,
                    "degree_type_id": normalized_degree_type_id,
                    "degree": degree,
                    "institution": institution,
                    "start_date": start_date,
                    "end_date": end_date,
                    "status": status,
                }

    def update_education(self, user_id: str, education_id: str, data: dict) -> dict[str, Any]:
        degree = self._normalize_required_text(data.get("degree"), "degree")
        institution = self._normalize_required_text(data.get("institution"), "institution")
        start_date = self._normalize_optional_date(data.get("start_date"), "start_date")
        end_date = self._normalize_optional_date(data.get("end_date"), "end_date")
        self._ensure_date_order(start_date, end_date, "start_date", "end_date")
        status = self._normalize_optional_text(data.get("status"))

        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_profile_exists(cur, user_id)
                normalized_degree_type_id = self._normalize_optional_degree_type_id(cur, data.get("degree_type_id"))
                cur.execute(
                    """
                    UPDATE profile_education
                    SET degree_type_id = %s,
                        degree = %s,
                        institution = %s,
                        start_date = %s::date,
                        end_date = %s::date,
                        status = %s,
                        updated_at = NOW()
                    WHERE profile_id = %s AND id = %s
                    RETURNING id
                    """,
                    (normalized_degree_type_id, degree, institution, start_date, end_date, status, user_id, education_id),
                )
                if cur.fetchone() is None:
                    raise ValueError("Education item not found")
                return {
                    "id": education_id,
                    "degree_type_id": normalized_degree_type_id,
                    "degree": degree,
                    "institution": institution,
                    "start_date": start_date,
                    "end_date": end_date,
                    "status": status,
                }

    def delete_education(self, user_id: str, education_id: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_profile_exists(cur, user_id)
                cur.execute(
                    "DELETE FROM profile_education WHERE profile_id = %s AND id = %s RETURNING id",
                    (user_id, education_id),
                )
                if cur.fetchone() is None:
                    raise ValueError("Education item not found")
