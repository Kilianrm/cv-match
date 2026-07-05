# Service Definition: Profile Service

## 1) Purpose

Primary responsibility:

The Profile Service owns user profile persistence and the review workflow for CV-parsed suggestions.

## 2) Responsibilities in Parse Workflow

- Accept parsed suggestion payloads from CV Parser Service.
- Persist suggestion batches and items for user review.
- Expose review endpoints for accept/decline decisions (bulk, section, item level).
- Apply only accepted suggestions to canonical profile tables.
- Preserve manual user edits as source of truth unless the user explicitly confirms replacements.

## 3) Data Ownership

Canonical profile tables:
- `profiles`
- `profile_skills`
- `profile_experience`
- `profile_education`
- `profile_certifications`

Suggestion workflow tables:
- `parse_suggestion_batches`
- `parse_suggestion_items`

Ownership rule:
- CV Parser never writes canonical profile tables directly.
- Profile Service is the only writer of canonical profile data and suggestion decision states.

## 4) Internal APIs

- `POST /internal/users/{user_id}/parse-suggestions` - persist normalized parser suggestions as pending review.
- `GET /internal/users/{user_id}/parse-suggestions` - fetch pending/recent suggestion batches.
- `POST /internal/users/{user_id}/parse-suggestions/decisions` - accept/decline decisions by section or item.
- `POST /internal/users/{user_id}/parse-suggestions/apply` - apply accepted suggestions to canonical profile tables.

## 5) UX Contract Expectations

- Suggestions are visible to users before persistence to canonical profile fields.
- Users can accept or decline by section.
- Users can accept all or decline all for a parse batch.
- Applied changes are explicit and traceable.

## 6) Guardrails

- No silent overwrite of non-empty canonical profile values.
- Conflicts between existing values and parsed suggestions are flagged for review.
- All decision actions are idempotent and safe to retry.

## 7) CV Retention Policy

- Keep one active CV per user (`cv_upload_records.is_active = true`).
- Keep older CV records as inactive history for audit/review continuity.
- Suggestion batches remain linked to the originating CV upload record.
- Accepting or rejecting suggestions never deletes the active CV artifact.

## 8) Merge and Conflict Rules (Apply Step)

Skills overlap:
- Normalize skill labels before matching.
- If the skill already exists, do not insert duplicates.
- If suggested proficiency conflicts with existing proficiency, mark as conflict and require explicit decision.

Experience overlap/timeline conflict:
- Detect probable overlap using company + position similarity + date range intersection.
- If probable same role, require one of: `merge`, `replace_existing`, or `keep_existing`.
- If not confidently same role, allow `add_separate`.
- Reject invalid timeline writes (for example end date before start date).

Decision actions supported:
- `keep_existing`
- `replace_existing`
- `merge`
- `add_separate`
- `reject`

Apply semantics:
- Only `accepted` suggestion items are eligible for apply.
- Apply writes canonical tables in a transaction per batch.
- Successfully applied items transition `accepted -> applied`.
