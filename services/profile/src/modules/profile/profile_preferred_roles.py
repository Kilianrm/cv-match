from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4


class ProfilePreferredRolesStoreMixin:
    def _normalize_optional_role_id(self, cur, role_id: str | None) -> str | None:
        normalized = self._normalize_optional_text(role_id)
        if not normalized:
            return None

        try:
            normalized = str(UUID(normalized))
        except ValueError as exc:
            raise ValueError("role_id must be a valid UUID") from exc

        cur.execute("SELECT 1 FROM roles WHERE id = %s", (normalized,))
        if cur.fetchone() is None:
            raise ValueError("role_id does not exist")

        return normalized

    def add_preferred_role(self, user_id: str, role_name: str, role_id: str | None = None) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_profile_exists(cur, user_id)
                normalized_role = self._normalize_required_text(role_name, "role_name")
                normalized_role_id = self._normalize_optional_role_id(cur, role_id)

                cur.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM profile_preferred_roles WHERE profile_id = %s",
                    (user_id,),
                )
                next_sort_order = cur.fetchone()[0]

                preferred_role_id = str(uuid4())
                try:
                    cur.execute(
                        """
                        INSERT INTO profile_preferred_roles (id, profile_id, role_id, role_name, normalized_role, sort_order)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (preferred_role_id, user_id, normalized_role_id, normalized_role, normalized_role.lower(), next_sort_order),
                    )
                except Exception as exc:
                    if "profile_preferred_roles_profile_id_normalized_role_key" in str(exc):
                        raise ValueError("Role already exists in profile") from exc
                    raise
                return {"id": preferred_role_id, "role_id": normalized_role_id, "role_name": normalized_role}

    def update_preferred_role(
        self,
        user_id: str,
        preferred_role_id: str,
        role_name: str,
        role_id: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_profile_exists(cur, user_id)
                normalized_role = self._normalize_required_text(role_name, "role_name")
                normalized_role_id = self._normalize_optional_role_id(cur, role_id)
                cur.execute(
                    """
                    UPDATE profile_preferred_roles
                    SET role_id = %s,
                        role_name = %s,
                        normalized_role = %s,
                        updated_at = NOW()
                    WHERE profile_id = %s AND id = %s
                    RETURNING id
                    """,
                    (normalized_role_id, normalized_role, normalized_role.lower(), user_id, preferred_role_id),
                )
                if cur.fetchone() is None:
                    raise ValueError("Preferred role not found")
                return {"id": preferred_role_id, "role_id": normalized_role_id, "role_name": normalized_role}

    def delete_preferred_role(self, user_id: str, preferred_role_id: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_profile_exists(cur, user_id)
                cur.execute(
                    "DELETE FROM profile_preferred_roles WHERE profile_id = %s AND id = %s RETURNING id",
                    (user_id, preferred_role_id),
                )
                if cur.fetchone() is None:
                    raise ValueError("Preferred role not found")
