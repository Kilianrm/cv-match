#!/usr/bin/env python3
"""Bootstrap CV Match PostgreSQL schema and seed catalogs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

USERS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
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

PROFILE_SCHEMA_SQL = """
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
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_cv_upload_records_one_active_per_user
ON cv_upload_records (user_id)
WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    full_name TEXT NOT NULL,
    headline TEXT,
    location TEXT,
    summary TEXT,
    country_code VARCHAR(2),
    region_id UUID REFERENCES regions(id),
    city_id UUID REFERENCES cities(id),
    years_experience INTEGER,
    work_mode_preference TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS profile_skills (
    id UUID PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id),
    proficiency_level TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (profile_id, skill_id)
);

CREATE TABLE IF NOT EXISTS profile_preferred_roles (
    id UUID PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id),
    role_name TEXT NOT NULL,
    normalized_role TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (profile_id, normalized_role)
);

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
);

CREATE TABLE IF NOT EXISTS profile_education (
    id UUID PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    degree_type_id UUID REFERENCES degree_types(id),
    degree TEXT NOT NULL,
    institution TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    status TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS profile_certifications (
    id UUID PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    issuer TEXT NOT NULL,
    issued_at DATE,
    expires_at DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE profile_preferred_roles
ADD COLUMN IF NOT EXISTS role_id UUID;

ALTER TABLE profile_education
ADD COLUMN IF NOT EXISTS degree_type_id UUID;

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
$$;

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
$$;

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
$$;

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
$$;

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
$$;
"""

VERIFY_TABLES = [
    "users",
    "countries",
    "regions",
    "cities",
    "skills",
    "roles",
    "degree_types",
    "profiles",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap schema and seed catalogs for cv-match")
    parser.add_argument("--database-url", required=True, help="PostgreSQL connection URL")
    parser.add_argument(
        "--reference-seed-dir",
        default="db/init",
        help="Directory containing reference seed SQL files (relative to repo root if not absolute)",
    )
    parser.add_argument(
        "--dev-seed-dir",
        default="db/seed/dev",
        help="Directory containing dev-only seed SQL files (relative to repo root if not absolute)",
    )
    parser.add_argument(
        "--seed-scope",
        choices=["reference", "dev", "all"],
        default="reference",
        help="Seed scope: reference (safe for all envs), dev (dev-only), or all",
    )
    parser.add_argument("--verify", action="store_true", help="Run post-bootstrap verification queries")
    return parser.parse_args()


def seed_files(seed_dir: Path) -> list[Path]:
    files = sorted(seed_dir.glob("*.sql"))
    if not files:
        raise FileNotFoundError(f"No .sql files found in seed directory: {seed_dir}")
    return files


def run() -> int:
    args = parse_args()

    repo_root = Path(__file__).resolve().parents[2]

    reference_seed_dir = Path(args.reference_seed_dir)
    if not reference_seed_dir.is_absolute():
        # Scripts are run from infra/cdk by npm, so resolve from repository root.
        reference_seed_dir = (repo_root / reference_seed_dir).resolve()

    reference_files = seed_files(reference_seed_dir)

    dev_seed_dir = Path(args.dev_seed_dir)
    if not dev_seed_dir.is_absolute():
        dev_seed_dir = (repo_root / dev_seed_dir).resolve()

    dev_files: list[Path] = []
    if args.seed_scope in ("dev", "all"):
        if dev_seed_dir.exists() and dev_seed_dir.is_dir():
            dev_files = sorted(dev_seed_dir.glob("*.sql"))
            if not dev_files:
                print(f"[bootstrap] warning: no dev seed files found in {dev_seed_dir}")
        else:
            print(f"[bootstrap] warning: dev seed directory not found: {dev_seed_dir}")

    try:
        from psycopg import connect
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "psycopg is required. Install dependencies with: pip install -r services/profile-service/requirements.txt"
        ) from exc

    with connect(args.database_url) as conn:
        with conn.cursor() as cur:
            print("[bootstrap] applying users schema")
            cur.execute(USERS_SCHEMA_SQL)

            for sql_file in reference_files:
                print(f"[bootstrap] applying reference seed: {sql_file.name}")
                cur.execute(sql_file.read_text(encoding="utf-8"))

            for sql_file in dev_files:
                print(f"[bootstrap] applying dev seed: {sql_file.name}")
                cur.execute(sql_file.read_text(encoding="utf-8"))

            print("[bootstrap] applying profile schema")
            cur.execute(PROFILE_SCHEMA_SQL)

        conn.commit()

        if args.verify:
            with conn.cursor() as cur:
                print("[bootstrap] verification:")
                for table in VERIFY_TABLES:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cur.fetchone()[0]
                    print(f"  - {table}: {count}")

    print("[bootstrap] completed successfully")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception as exc:
        print(f"[bootstrap] failed: {exc}", file=sys.stderr)
        raise
