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
                                summary TEXT,
                                country_code TEXT,
                                region_id UUID,
                                city_id UUID,
                                years_experience INTEGER,
                                work_mode_preference TEXT,
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
                    SELECT
                        u.email,
                        p.full_name,
                        p.headline,
                        p.summary,
                        p.country_code,
                        p.region_id,
                        p.city_id,
                        p.years_experience,
                        p.work_mode_preference,
                        c.name AS country_name,
                        r.name AS region_name,
                        ci.name AS city_name,
                        p.location
                    FROM profiles p
                    JOIN users u ON u.id = p.user_id
                    LEFT JOIN countries c ON c.code = p.country_code
                    LEFT JOIN regions r ON r.id = p.region_id
                    LEFT JOIN cities ci ON ci.id = p.city_id
                    WHERE p.user_id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None

                (
                    email,
                    full_name,
                    headline,
                    summary,
                    country_code,
                    region_id,
                    city_id,
                    years_experience,
                    work_mode_preference,
                    country_name,
                    region_name,
                    city_name,
                    legacy_location,
                ) = row

                location_obj = {
                    "country": {"code": country_code, "name": country_name} if country_code else None,
                    "region": {"id": str(region_id), "name": region_name} if region_id else None,
                    "city": {"id": str(city_id), "name": city_name} if city_id else None,
                }

                # Keep a fallback for legacy profile rows that only have free-text location.
                profile_obj = {
                    "full_name": full_name,
                    "headline": headline,
                    "summary": summary,
                    "country_code": country_code,
                    "region_id": str(region_id) if region_id else None,
                    "city_id": str(city_id) if city_id else None,
                    "years_experience": years_experience,
                    "work_mode_preference": work_mode_preference,
                    "legacy_location": legacy_location,
                }

                return {
                    "user": {
                        "user_id": user_id,
                        "email": email,
                    },
                    "profile": profile_obj,
                    "location": location_obj,
                    "skills": [],
                    "preferred_roles": [],
                    "experience": [],
                    "education": [],
                    "certifications": [],
                    "cv": None,
                }

    def upsert_profile(self, user_id: str, data: dict) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO profiles (
                        user_id,
                        full_name,
                        headline,
                        location,
                        summary,
                        country_code,
                        region_id,
                        city_id,
                        years_experience,
                        work_mode_preference
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE
                        SET full_name = EXCLUDED.full_name,
                            headline = EXCLUDED.headline,
                            location = EXCLUDED.location,
                            summary = EXCLUDED.summary,
                            country_code = EXCLUDED.country_code,
                            region_id = EXCLUDED.region_id,
                            city_id = EXCLUDED.city_id,
                            years_experience = EXCLUDED.years_experience,
                            work_mode_preference = EXCLUDED.work_mode_preference,
                            updated_at = NOW()
                    """,
                    (
                        user_id,
                        data.get("full_name"),
                        data.get("headline"),
                        data.get("location"),
                        data.get("summary"),
                        data.get("country_code"),
                        data.get("region_id"),
                        data.get("city_id"),
                        data.get("years_experience"),
                        data.get("work_mode_preference"),
                    ),
                )
