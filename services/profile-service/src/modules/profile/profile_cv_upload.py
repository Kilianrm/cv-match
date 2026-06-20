from __future__ import annotations

from typing import Any
from uuid import uuid4


class ProfileCvUploadStoreMixin:
    def _ensure_user_exists(self, cur, user_id: str) -> None:
        cur.execute("SELECT 1 FROM users WHERE id = %s", (user_id,))
        if cur.fetchone() is None:
            raise ValueError("User not found")

    def register_cv_upload(
        self,
        user_id: str,
        original_filename: str,
        storage_key: str,
        content_type: str,
        parse_status: str = "pending",
    ) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_user_exists(cur, user_id)

                cur.execute(
                    """
                    UPDATE cv_upload_records
                    SET is_active = FALSE
                    WHERE user_id = %s AND is_active = TRUE
                    """,
                    (user_id,),
                )

                cv_id = str(uuid4())
                cur.execute(
                    """
                    INSERT INTO cv_upload_records (
                        id, user_id, original_filename, storage_key, content_type, parse_status, is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                    RETURNING id, uploaded_at, parse_status, is_active
                    """,
                    (cv_id, user_id, original_filename, storage_key, content_type, parse_status),
                )
                row = cur.fetchone()

                return {
                    "id": str(row[0]),
                    "uploaded_at": row[1].isoformat(),
                    "parse_status": row[2],
                    "is_active": row[3],
                    "storage_key": storage_key,
                    "original_filename": original_filename,
                    "content_type": content_type,
                }

    def get_active_cv(self, user_id: str) -> dict[str, Any] | None:
        """Retrieve the active CV upload record for a user, or None if no active CV exists."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, original_filename, storage_key, content_type, parse_status, uploaded_at
                    FROM cv_upload_records
                    WHERE user_id = %s AND is_active = TRUE
                    LIMIT 1
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None

                return {
                    "id": str(row[0]),
                    "original_filename": row[1],
                    "storage_key": row[2],
                    "content_type": row[3],
                    "parse_status": row[4],
                    "uploaded_at": row[5].isoformat(),
                }

    def deactivate_active_cv(self, user_id: str) -> bool:
        """Deactivate the current active CV for a user. Returns True when one was deactivated."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_user_exists(cur, user_id)
                cur.execute(
                    """
                    UPDATE cv_upload_records
                    SET is_active = FALSE
                    WHERE user_id = %s AND is_active = TRUE
                    RETURNING id
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                return row is not None