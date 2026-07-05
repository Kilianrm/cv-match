from __future__ import annotations

import time

from psycopg import OperationalError


class ProfileSchemaMixin:
    """Owns profile module schema bootstrap.

    This mixin is responsible for creating/ensuring profile-related tables at
    startup and retrying while PostgreSQL becomes ready. It intentionally keeps
    only schema initialization concerns and excludes business validation and
    CRUD behavior.
    """

    def _initialize_schema(self) -> None:
        for attempt in range(1, self._max_init_retries + 1):
            try:
                with self._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS cv_upload_records (
                                id UUID PRIMARY KEY,
                                user_id UUID NOT NULL REFERENCES users(id),
                                original_filename VARCHAR NOT NULL,
                                storage_key VARCHAR NOT NULL,
                                content_type VARCHAR NOT NULL,
                                parse_status VARCHAR NOT NULL,
                                parse_error_code VARCHAR,
                                uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                parsed_at TIMESTAMPTZ,
                                is_active BOOLEAN NOT NULL DEFAULT FALSE
                            )
                            """
                        )
                        cur.execute(
                            """
                            CREATE UNIQUE INDEX IF NOT EXISTS uq_cv_upload_records_one_active_per_user
                            ON cv_upload_records (user_id)
                            WHERE is_active = TRUE
                            """
                        )
                        cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS profiles (
                                user_id UUID PRIMARY KEY REFERENCES users(id),
                                full_name TEXT NOT NULL,
                                headline TEXT,
                                location TEXT,
                                summary TEXT,
                                country_code VARCHAR(2),
                                region_id UUID,
                                city_id UUID,
                                years_experience INTEGER,
                                work_mode_preference TEXT,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            )
                            """
                        )
                        cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS profile_skills (
                                id UUID PRIMARY KEY,
                                profile_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
                                skill_id UUID NOT NULL,
                                proficiency_level TEXT,
                                sort_order INTEGER NOT NULL DEFAULT 0,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                UNIQUE (profile_id, skill_id)
                            )
                            """
                        )
                        cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS profile_preferred_roles (
                                id UUID PRIMARY KEY,
                                profile_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
                                role_id UUID,
                                role_name TEXT NOT NULL,
                                normalized_role TEXT NOT NULL,
                                sort_order INTEGER NOT NULL DEFAULT 0,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                UNIQUE (profile_id, normalized_role)
                            )
                            """
                        )
                        cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS profile_experience (
                                id UUID PRIMARY KEY,
                                profile_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
                                position TEXT NOT NULL,
                                company TEXT NOT NULL,
                                start_date DATE NOT NULL,
                                end_date DATE,
                                is_current BOOLEAN NOT NULL DEFAULT FALSE,
                                responsibilities JSONB,
                                sort_order INTEGER NOT NULL DEFAULT 0,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            )
                            """
                        )
                        cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS profile_education (
                                id UUID PRIMARY KEY,
                                profile_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
                                degree_type_id UUID,
                                degree TEXT NOT NULL,
                                institution TEXT NOT NULL,
                                start_date DATE,
                                end_date DATE,
                                status TEXT,
                                sort_order INTEGER NOT NULL DEFAULT 0,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            )
                            """
                        )
                        cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS profile_certifications (
                                id UUID PRIMARY KEY,
                                profile_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
                                name TEXT NOT NULL,
                                issuer TEXT NOT NULL,
                                issued_at DATE,
                                expires_at DATE,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            )
                            """
                        )
                        # Backfill schema drift for environments where tables existed
                        # before role_id/degree_type_id columns were introduced.
                        cur.execute(
                            """
                            ALTER TABLE profile_preferred_roles
                            ADD COLUMN IF NOT EXISTS role_id UUID
                            """
                        )
                        cur.execute(
                            """
                            ALTER TABLE profile_education
                            ADD COLUMN IF NOT EXISTS degree_type_id UUID
                            """
                        )

                        cur.execute(
                            """
                            DO $$
                            BEGIN
                                IF to_regclass('public.regions') IS NULL THEN
                                    RETURN;
                                END IF;

                                IF NOT EXISTS (
                                    SELECT 1
                                    FROM pg_constraint
                                    WHERE conname = 'profiles_region_id_fkey'
                                ) THEN
                                    ALTER TABLE profiles
                                    ADD CONSTRAINT profiles_region_id_fkey
                                    FOREIGN KEY (region_id) REFERENCES regions(id);
                                END IF;
                            END
                            $$
                            """
                        )
                        cur.execute(
                            """
                            DO $$
                            BEGIN
                                IF to_regclass('public.cities') IS NULL THEN
                                    RETURN;
                                END IF;

                                IF NOT EXISTS (
                                    SELECT 1
                                    FROM pg_constraint
                                    WHERE conname = 'profiles_city_id_fkey'
                                ) THEN
                                    ALTER TABLE profiles
                                    ADD CONSTRAINT profiles_city_id_fkey
                                    FOREIGN KEY (city_id) REFERENCES cities(id);
                                END IF;
                            END
                            $$
                            """
                        )
                        cur.execute(
                            """
                            DO $$
                            BEGIN
                                IF to_regclass('public.skills') IS NULL THEN
                                    RETURN;
                                END IF;

                                IF NOT EXISTS (
                                    SELECT 1
                                    FROM pg_constraint
                                    WHERE conname = 'profile_skills_skill_id_fkey'
                                ) THEN
                                    ALTER TABLE profile_skills
                                    ADD CONSTRAINT profile_skills_skill_id_fkey
                                    FOREIGN KEY (skill_id) REFERENCES skills(id);
                                END IF;
                            END
                            $$
                            """
                        )
                        cur.execute(
                            """
                            DO $$
                            BEGIN
                                IF to_regclass('public.roles') IS NULL THEN
                                    RETURN;
                                END IF;

                                IF NOT EXISTS (
                                    SELECT 1
                                    FROM pg_constraint
                                    WHERE conname = 'profile_preferred_roles_role_id_fkey'
                                ) THEN
                                    ALTER TABLE profile_preferred_roles
                                    ADD CONSTRAINT profile_preferred_roles_role_id_fkey
                                    FOREIGN KEY (role_id) REFERENCES roles(id);
                                END IF;
                            END
                            $$
                            """
                        )
                        cur.execute(
                            """
                            DO $$
                            BEGIN
                                IF to_regclass('public.degree_types') IS NULL THEN
                                    RETURN;
                                END IF;

                                IF NOT EXISTS (
                                    SELECT 1
                                    FROM pg_constraint
                                    WHERE conname = 'profile_education_degree_type_id_fkey'
                                ) THEN
                                    ALTER TABLE profile_education
                                    ADD CONSTRAINT profile_education_degree_type_id_fkey
                                    FOREIGN KEY (degree_type_id) REFERENCES degree_types(id);
                                END IF;
                            END
                            $$
                            """
                        )
                return
            except OperationalError:
                if attempt == self._max_init_retries:
                    raise
                time.sleep(self._retry_delay_seconds)
