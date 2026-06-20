# Database Schema

## Purpose

Define the shared PostgreSQL data model for CV Match, including user identities, CV records, profiles, job offers, match results, notification preferences, and service-run metadata. The database is the system of record for business data, while file storage and background services handle large artifacts and asynchronous processing.

## Design Principles

- Single source of truth: each business entity has one canonical record in the database.
- User ownership: user-related data is always linked to the authenticated Cognito identity.
- Separation of concerns: raw files live in object storage, while structured metadata and results live in PostgreSQL.
- Async-friendly modeling: long-running processes store job state, status, and timestamps so the frontend can poll safely.
- Minimal duplication: derived data is stored only when it improves query speed or UX; otherwise it should be computed on demand.
- Traceability: important state changes keep timestamps and correlation fields for auditability and debugging.
- Safe deletion and retention: personal data and generated artifacts follow explicit lifecycle and retention rules.

## Core Entities

### Users

Primary table for authenticated application users.

Key fields:
- `id` (internal primary key)
- `cognito_sub` (Cognito identity reference)
- `email`
- `email_verified`
- `status` (for example: active, suspended, deleted)
- `last_synced_from_cognito_at` (nullable)
- `created_at`
- `updated_at`

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- One row per application user.
- `cognito_sub` must be unique and is the main link between Cognito and the database user record.
- This table is the identity bridge (`cognito_sub -> id`) for the rest of the business schema.
- `email` is an account attribute synchronized from Cognito, not the primary identity key.

### CV Upload Records

Stores CV upload artifact metadata, storage references, and parsing lifecycle status.

Key fields:
- `id`
- `user_id`
- `original_filename`
- `storage_key` (object storage reference)
- `content_type`
- `parse_status` (pending, processing, completed, failed)
- `parse_error_code` (nullable)
- `uploaded_at`
- `parsed_at` (nullable)
- `is_active`

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- The database stores metadata, not the raw file bytes.
- A user can have multiple CV upload records over time; exactly one can be marked active.
- The uploaded file binary is stored in object storage (S3) and referenced by `storage_key`.
- Parsed structured output from that CV is persisted in database profile tables (`Profiles`, `Skills`, `Profile Skills`, `Profile Preferred Roles`, `Profile Experience`, `Profile Education`, and `Profile Certifications`).

### Profiles

Stores the structured user profile used for matching and presentation.

Key fields:
- `user_id`
- `full_name`
- `headline`
- `summary`
- `country_code` (ISO 3166-1 alpha-2)
- `region_id` (nullable reference to `Regions`)
- `city_id` (nullable reference to `Cities`)
- `years_experience`
- `work_mode_preference`
- `created_at`
- `updated_at`

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- This table is the canonical source for the user's public profile data.
- CV parsing can populate or refresh profile content.
- The API `GET /profile` response is assembled from this table plus related profile sub-entities.
- `GET /profile` also joins identity fields from `Users` (for example `email`) and CV summary fields from `CV Upload Records`.
- The API can still expose a single `location` display string by composing normalized city, region, and country metadata.
- Manual edits are first-class and can overwrite auto-filled values.
- Parsed CV data is materialized here and in profile sub-entities, not stored as file content.
- Keep derived fields (for example profile completion percentage) outside this table and compute them in the service layer.
- The legacy `location` text remains for backward compatibility while normalized location references (`country_code`, `region_id`, `city_id`) are used for consistency.

### Location Reference Data

Stores normalized location values used by profile validation, filtering, and matching.

#### Countries

Key fields:
- `code` (ISO 3166-1 alpha-2 primary key)
- `name`
- `normalized_name`
- `created_at`
- `updated_at`

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- This is the canonical country catalog for profile and job normalization.
- `Profiles.country_code` should always reference this table.

#### Regions

Key fields:
- `id`
- `country_code`
- `name`
- `normalized_name`
- `code` (nullable local administrative code)
- `created_at`
- `updated_at`

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- Stores normalized first-level administrative divisions such as states, provinces, or autonomous communities.
- Unique by country plus normalized name.

#### Cities

Key fields:
- `id`
- `country_code`
- `region_id` (nullable)
- `name`
- `normalized_name`
- `created_at`
- `updated_at`

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- Stores normalized city values used by profile matching and filtering.
- `region_id` can be nullable for countries where region coverage is incomplete during early rollout.
- Unique by country, region, and normalized name.

### Skills

Global catalog of normalized skills available across the platform.

Key fields:
- `id`
- `skill_name`
- `normalized_skill`
- `category` (for example: backend, cloud, data)
- `created_at`
- `updated_at`

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- One row per canonical skill label.
- Used to keep skill naming consistent across profiles, matching, and search.

### Roles

Global catalog of normalized role targets available across the platform.

Key fields:
- `id`
- `role_name`
- `normalized_role`
- `category` (for example: engineering, data, product)
- `created_at`
- `updated_at`

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- One row per canonical role label.
- Keeps role naming consistent across profile preferences, filtering, and ranking.

### Role Aliases

Alias map for role normalization.

Key fields:
- `id`
- `role_id`
- `alias`
- `normalized_alias`
- `created_at`

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- Useful for mapping close variants (for example `fullstack engineer` -> `full stack engineer`).

### Profile Skills

User-specific skill assignments for a profile, including proficiency metadata.

Key fields:
- `id`
- `profile_id`
- `skill_id`
- `proficiency_level` (optional)
- `sort_order`

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- Links a profile to a global skill from `Skills`.
- Stores user-specific metadata such as proficiency level and display order.
- Multiple skills can be linked to the same profile, and the same global skill can be reused by many profiles.

### Profile Preferred Roles

Normalized list of role targets selected or inferred for a profile.

Key fields:
- `id`
- `profile_id`
- `role_id` (nullable reference to `Roles`)
- `role_name`
- `normalized_role`
- `sort_order`

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- Represents the `preferred_roles` array from `GET /profile`.
- `role_id` is optional and used when a role maps to the seeded role catalog.
- Keeping roles normalized helps filtering and ranking against job titles.

### Profile Experience

Work history records associated with a profile.

Key fields:
- `id`
- `profile_id`
- `position`
- `company`
- `start_date`
- `end_date` (nullable)
- `is_current`
- `responsibilities` (array or JSON list)
- `sort_order`

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- Represents the `experience` array from `GET /profile`.
- Can be sourced from CV parsing and later edited by the user.

### Profile Education

Education history records associated with a profile.

Key fields:
- `id`
- `profile_id`
- `degree_type_id` (nullable reference to `Degree Types`)
- `degree`
- `institution`
- `start_date` (nullable)
- `end_date` (nullable)
- `status` (for example: completed, in_progress, dropped)
- `sort_order`

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- Represents the `education` array from `GET /profile`.
- Keeps `degree` and `institution` as user-editable text while optional `degree_type_id` adds controlled normalization.
- Stored separately so profile retrieval stays rich without overloading the base profile row.

### Degree Types

Global catalog of normalized degree levels used by profile education.

Key fields:
- `id`
- `degree_name`
- `normalized_degree`
- `level`
- `created_at`
- `updated_at`

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- Intentionally small and stable catalog for consistent reporting and matching.
- Institutions remain free text at this stage to avoid large, high-maintenance global seeding.

### Profile Certifications

Professional certifications associated with a profile.

Key fields:
- `id`
- `profile_id`
- `name`
- `issuer`
- `issued_at` (nullable)
- `expires_at` (nullable)

Notes:
- Owner service: [PROFILE Service](services/1-profile-service.md)
- Represents the `certifications` array from `GET /profile`.
- Useful for filtering and relevance scoring in matching.

### Job Offers

Canonical job posting data used for matching.

Key fields:
- `id`
- `external_source`
- `external_job_id`
- `title`
- `company`
- `country_code` (nullable ISO 3166-1 alpha-2 reference)
- `region_id` (nullable reference to `Regions`)
- `city_id` (nullable reference to `Cities`)
- `raw_location` (nullable original source location text)
- `work_mode`
- `employment_type`
- `seniority`
- `salary_min`
- `salary_max`
- `salary_currency`
- `posted_at`
- `apply_url`
- `source_url`
- `status` (for example: active, expired, archived)

Notes:
- Owner service: [Job Scraper Service](services/3-scraper-service.md)
- Job offers can come from multiple sources and should be deduplicated by source identity.
- Matching and filtering should use normalized location references when available.
- `raw_location` preserves the original scraped location text for audit and re-normalization.
- Matching logic reads from this table, but the UI should only see user-facing offer data.

### Matches

Represents the ranked relationship between a user profile and a job offer.

Key fields:
- `id`
- `user_id`
- `profile_id`
- `job_offer_id`
- `candidate_snapshot_id` (nullable reference to candidate snapshot)
- `job_snapshot_id` (nullable reference to job snapshot)
- `scoring_version`
- `score_total`
- `score_breakdown` (jsonb)
- `ranked_position` (nullable)
- `match_status` (for example: scored, accepted, rejected)
- `matched_at`
- `updated_at`
- `rank_reason_summary` (optional)

Notes:
- Owner service: [Matching Service](services/4-matching-service.md)
- One match links one user profile to one job offer.
- The CV is used upstream to parse and enrich the profile, but it is not the main matching entity.
- Optimized CV output should be stored in a dedicated entity linked to the match, not embedded directly in this table.
- Detailed scoring inputs can remain internal, while a short summary can be exposed to the client.

### CV Optimization Records

Stores metadata and lifecycle state for generated CV optimizations tied to a specific match.

Key fields:
- `id`
- `match_id`
- `user_id`
- `storage_key` (object storage reference)
- `status` (pending, processing, completed, failed)
- `error_code` (nullable)
- `generated_at` (nullable)
- `expires_at` (nullable)
- `created_at`
- `updated_at`

Notes:
- Owner service: [CV Optimization Service](services/6-cv-optimizer-service.md)
- This table separates optimization lifecycle concerns from match scoring data.
- Generated optimized CV file binaries are stored in object storage (S3), while this table stores metadata and status.
- For the current product scope, enforce at most one optimization record per match.
- If versioning is needed later, this model can evolve without changing the `matches` table shape.

### Notification Preferences

Stores the user's current notification settings.

Key fields:
- `user_id`
- `email_enabled`
- `push_enabled`
- `whatsapp_enabled`
- `telegram_enabled`
- `sms_enabled`
- `frequency`
- `updated_at`

Notes:
- Owner service: [Notification Service](services/5-notification-service.md) (managed through API endpoint boundary).
- This is the source of truth for notification channel preferences.
- The API can expose a summary of this table in profile, but the dedicated endpoint remains the primary contract.

### Notification Deliveries

Tracks messages sent to users through each channel.

Key fields:
- `id`
- `user_id`
- `channel`
- `template_name`
- `status` (queued, sent, delivered, failed)
- `provider_message_id` (nullable)
- `sent_at` (nullable)
- `delivered_at` (nullable)
- `failed_at` (nullable)
- `error_code` (nullable)

Notes:
- Owner service: [Notification Service](services/5-notification-service.md)
- Used for delivery history, retries, and troubleshooting.
- This table is operational and should not be treated as user profile data.

## Implemented Tables (Current Runtime)

The following tables are currently present in `profile_db` (`public` schema) and are considered implemented in the local runtime:

- `cities`
- `countries`
- `cv_upload_records`
- `degree_types`
- `profile_certifications`
- `profile_education`
- `profile_experience`
- `profile_preferred_roles`
- `profile_skills`
- `profiles`
- `regions`
- `role_aliases`
- `roles`
- `skills`
- `users`

Verification query used:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```