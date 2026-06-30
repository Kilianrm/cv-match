from __future__ import annotations

from typing import Any
from uuid import uuid4


class ProfileCertificationsStoreMixin:
    def add_certification(self, user_id: str, data: dict) -> dict[str, Any]:
        name = self._normalize_required_text(data.get("name"), "name")
        issuer = self._normalize_required_text(data.get("issuer"), "issuer")
        issued_at = self._normalize_optional_date(data.get("issued_at"), "issued_at")
        expires_at = self._normalize_optional_date(data.get("expires_at"), "expires_at")
        self._ensure_date_order(issued_at, expires_at, "issued_at", "expires_at")

        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_profile_exists(cur, user_id)
                cert_id = str(uuid4())
                cur.execute(
                    """
                    INSERT INTO profile_certifications (id, profile_id, name, issuer, issued_at, expires_at)
                    VALUES (%s, %s, %s, %s, %s::date, %s::date)
                    """,
                    (cert_id, user_id, name, issuer, issued_at, expires_at),
                )
                return {
                    "id": cert_id,
                    "name": name,
                    "issuer": issuer,
                    "issued_at": issued_at,
                    "expires_at": expires_at,
                }

    def update_certification(self, user_id: str, cert_id: str, data: dict) -> dict[str, Any]:
        name = self._normalize_required_text(data.get("name"), "name")
        issuer = self._normalize_required_text(data.get("issuer"), "issuer")
        issued_at = self._normalize_optional_date(data.get("issued_at"), "issued_at")
        expires_at = self._normalize_optional_date(data.get("expires_at"), "expires_at")
        self._ensure_date_order(issued_at, expires_at, "issued_at", "expires_at")

        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_profile_exists(cur, user_id)
                cur.execute(
                    """
                    UPDATE profile_certifications
                    SET name = %s,
                        issuer = %s,
                        issued_at = %s::date,
                        expires_at = %s::date,
                        updated_at = NOW()
                    WHERE profile_id = %s AND id = %s
                    RETURNING id
                    """,
                    (name, issuer, issued_at, expires_at, user_id, cert_id),
                )
                if cur.fetchone() is None:
                    raise ValueError("Certification item not found")
                return {
                    "id": cert_id,
                    "name": name,
                    "issuer": issuer,
                    "issued_at": issued_at,
                    "expires_at": expires_at,
                }

    def delete_certification(self, user_id: str, cert_id: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_profile_exists(cur, user_id)
                cur.execute(
                    "DELETE FROM profile_certifications WHERE profile_id = %s AND id = %s RETURNING id",
                    (user_id, cert_id),
                )
                if cur.fetchone() is None:
                    raise ValueError("Certification item not found")
