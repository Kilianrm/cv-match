from __future__ import annotations

from dataclasses import dataclass
import time
import uuid

from psycopg import OperationalError, connect


@dataclass(frozen=True)
class SyncIdentityResult:
    internal_user_id: str
    created: bool


class UsersStore:
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
                            CREATE TABLE IF NOT EXISTS users (
                                id TEXT PRIMARY KEY,
                                cognito_sub TEXT NOT NULL,
                                email TEXT,
                                email_verified BOOLEAN NOT NULL DEFAULT FALSE,
                                status TEXT NOT NULL DEFAULT 'active',
                                last_synced_from_cognito_at TIMESTAMPTZ,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                UNIQUE(cognito_sub)
                            )
                            """
                        )
                return
            except OperationalError:
                if attempt == self._max_init_retries:
                    raise
                time.sleep(self._retry_delay_seconds)

    def sync_from_jwt(self, issuer: str, subject: str, email: str | None) -> SyncIdentityResult:
        _ = issuer
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE cognito_sub = %s
                    """,
                    (subject,),
                )
                existing = cur.fetchone()

                if existing:
                    if email is not None:
                        cur.execute(
                            """
                            UPDATE users
                            SET email = %s,
                                last_synced_from_cognito_at = NOW(),
                                updated_at = NOW()
                            WHERE cognito_sub = %s
                            """,
                            (email, subject),
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE users
                            SET last_synced_from_cognito_at = NOW(),
                                updated_at = NOW()
                            WHERE cognito_sub = %s
                            """,
                            (subject,),
                        )
                    return SyncIdentityResult(internal_user_id=str(existing[0]), created=False)

                internal_user_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO users (id, cognito_sub, email, email_verified, status, last_synced_from_cognito_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """,
                    (internal_user_id, subject, email, False, "active"),
                )
                inserted = cur.fetchone()
                if inserted:
                    return SyncIdentityResult(internal_user_id=str(inserted[0]), created=True)

                # Race-safe fallback in case another request inserted the same (issuer, subject).
                if email is not None:
                    cur.execute(
                        """
                        UPDATE users
                        SET email = %s,
                            last_synced_from_cognito_at = NOW(),
                            updated_at = NOW()
                        WHERE cognito_sub = %s
                        """,
                        (email, subject),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE users
                        SET last_synced_from_cognito_at = NOW(),
                            updated_at = NOW()
                        WHERE cognito_sub = %s
                        """,
                        (subject,),
                    )

                cur.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE cognito_sub = %s
                    """,
                    (subject,),
                )
                existing_after_conflict = cur.fetchone()
                if existing_after_conflict:
                    return SyncIdentityResult(internal_user_id=str(existing_after_conflict[0]), created=False)

                raise RuntimeError("Failed to synchronize identity mapping")
