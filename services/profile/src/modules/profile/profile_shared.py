from __future__ import annotations

from datetime import date


class ProfileSharedMixin:
    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized if normalized else None

    @staticmethod
    def _normalize_optional_date(value: str | None, field: str) -> str | None:
        normalized = ProfileSharedMixin._normalize_optional_text(value)
        if normalized is None:
            return None
        try:
            return date.fromisoformat(normalized).isoformat()
        except ValueError as exc:
            raise ValueError(f"{field} must be a valid date in YYYY-MM-DD format") from exc

    @staticmethod
    def _ensure_date_order(start_date: str | None, end_date: str | None, start_field: str, end_field: str) -> None:
        if start_date is None or end_date is None:
            return
        if date.fromisoformat(end_date) < date.fromisoformat(start_date):
            raise ValueError(f"{end_field} cannot be earlier than {start_field}")

    @staticmethod
    def _normalize_required_text(value: str | None, field: str) -> str:
        normalized = ProfileSharedMixin._normalize_optional_text(value)
        if not normalized:
            raise ValueError(f"{field} is required")
        return normalized

    @staticmethod
    def _normalize_token(value: str) -> str:
        return " ".join(value.lower().split())

    def _ensure_profile_exists(self, cur, user_id: str) -> None:
        cur.execute("SELECT 1 FROM profiles WHERE user_id = %s", (user_id,))
        if cur.fetchone() is None:
            raise ValueError("Profile not found")
