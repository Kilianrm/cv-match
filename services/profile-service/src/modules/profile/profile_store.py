from __future__ import annotations

import time

from psycopg import OperationalError, connect


class ProfileStore:
    def __init__(self, database_url: str, max_init_retries: int = 20, retry_delay_seconds: float = 1.0) -> None:
        self._database_url = database_url
        self._max_init_retries = max_init_retries
        self._retry_delay_seconds = retry_delay_seconds
        self._initialize_schema()

    def _connect(self):
        return connect(self._database_url)

    def _initialize_schema(self) -> None:
        for attempt in range(1, self._max_init_retries + 1):
            try:
                with self._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS profiles (
                                user_id TEXT PRIMARY KEY,
                                full_name TEXT NOT NULL,
                                headline TEXT,
                                location TEXT,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            )
                            """
                        )
                return
            except OperationalError:
                if attempt == self._max_init_retries:
                    raise
                time.sleep(self._retry_delay_seconds)

    def get_profile(self, user_id: str) -> dict | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT p.full_name, p.headline, p.location, u.email
                    FROM profiles p
                    JOIN users u ON u.id = p.user_id
                    WHERE p.user_id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return {
                    "user_id": user_id,
                    "full_name": row[0],
                    "headline": row[1],
                    "location": row[2],
                    "email": row[3],
                }

    def upsert_profile(self, user_id: str, data: dict) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO profiles (user_id, full_name, headline, location)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE
                        SET full_name = EXCLUDED.full_name,
                            headline = EXCLUDED.headline,
                            location = EXCLUDED.location,
                            updated_at = NOW()
                    """,
                    (
                        user_id,
                        data.get("full_name"),
                        data.get("headline"),
                        data.get("location"),
                    ),
                )
