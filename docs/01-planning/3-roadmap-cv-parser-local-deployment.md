# Roadmap: CV Parser Local Deployment

## Purpose

Deliver the first end-to-end local CV parsing workflow after upload, without cloud dependency. This roadmap extends the current profile-first local MVP by adding asynchronous parser processing, parse status lifecycle, and a user review workflow where parsed data must be accepted or rejected before profile persistence.

## Approach

- Keep deployment local-first using Docker Compose and LocalStack only.
- Implement parser as an isolated worker service consuming SQS-style events from LocalStack.
- Keep strict ownership boundaries: `cv-parser-service` only parses/normalizes CV content; `profile-service` owns parsed suggestion data and all review/apply decisions.
- Favor idempotent writes and retry-safe flows before introducing advanced extraction features.

## User Journeys In Scope

1. **Upload and Queue Parse** - User uploads CV and receives immediate `202 Accepted` while parse is queued.
2. **Async Parse Completion** - Parser consumes `parse_cv_requested`, reads CV from storage, extracts profile fields, and sends normalized suggestions to Profile Service.
3. **Review Suggestions** - User reviews parsed suggestions by section and chooses accept or reject.
4. **Apply Confirmed Changes** - Only accepted suggestions are applied to canonical profile tables.
5. **Parse Failure Visibility** - Invalid/corrupted CVs are marked as failed with an error code and visible status in profile/CV metadata.
6. **Onboarding Skip and Resume** - User can skip review during onboarding and resume from profile later without losing pending suggestions.

## Infrastructure

- Docker Compose services: `gateway-service`, `profile-service`, `cv-parser-service`, `postgres`, `localstack`.
- LocalStack simulates:
  - S3 bucket for CV files.
  - SQS parser queue plus DLQ.
- Parser worker runs as an internal service with no public ingress.
- Internal communication over Docker network; event flow remains async.
- Data persistence handoff: `cv-parser-service` sends normalized suggestion payloads to `profile-service`, and `profile-service` persists and manages them in PostgreSQL.

## Tables Required

New tables introduced in this roadmap:

- `parse_suggestion_batches`
- `parse_suggestion_items`

## Endpoints

**Gateway (Public):**
- `POST /api/v1/profile/cv` - upload CV and publish `parse_cv_requested`.
- `GET /api/v1/profile/cv` - return active CV metadata including `parse_status`.
- `DELETE /api/v1/profile/cv` - delete active CV metadata and object.
- `GET /api/v1/profile` - return full profile including parsed sections and CV summary.

**CV Parser Service (Internal Worker):**
- Queue consumer for `parse_cv_requested` messages (queue owned by `cv-parser-service`).
- `GET /health`

Notes:
- Profile internal endpoints are intentionally out of scope for this roadmap.
- This roadmap focuses on the event contract (`parse_cv_requested`) and parser consumption lifecycle.
- The persistence integration path is explicitly `cv-parser-service -> profile-service -> PostgreSQL`.
- Ownership is explicit: `profile-service` is the source of truth for parsed suggestion state and canonical profile writes.

## Implementation Order

1. **Compose baseline** - Add `cv-parser-service` to local compose stack and wire env vars for queue/storage/profile-service integration.
2. **Queue and storage bootstrap** - Ensure LocalStack S3 bucket, parser queue, and parser DLQ exist in local startup scripts.
3. **Upload event contract** - Confirm upload flow persists metadata and publishes `parse_cv_requested` with `user_id`, `cv_id`, and trace fields.
4. **Parser worker skeleton** - Implement message polling, visibility timeout handling, graceful shutdown, and structured logging.
5. **Parsing core v1 (MVP)** - Implement parser adapters, text extraction, section segmentation, and normalized output contract per section.
6. **CV extraction pipeline integration** - Download CV from S3, run parsing core, produce confidence-scored suggestion payload.
7. **Suggestion draft integration** - Send normalized payload to Profile internal endpoint for `parse_suggestion_batches` and `parse_suggestion_items` persistence.
8. **Review decision contract** - Add gateway/profile review endpoints for accept/decline by section and bulk apply.
9. **Parse status transitions** - Update lifecycle (`pending -> processing -> completed|failed`) with retry-safe behavior.
10. **Conflict resolution logic** - Implement deterministic merge rules for skill overlaps and experience timeline conflicts.
11. **CV retention policy** - Keep active CV available after review decisions; keep historical records inactive.
12. **Failure path and DLQ** - Handle unsupported/corrupted CVs and transient failures with retries and final DLQ routing.
13. **Frontend review UX pass** - Validate onboarding flow (accept/decline/skip), conflict handling, and parse status visibility.
14. **CI local pipeline updates** - Run parser unit/integration suites plus review-flow integration checks.

## Tests

**CV Parser Service:**
- Unit: extraction and normalization logic by CV samples.
- Integration: queue consume -> S3 read -> profile suggestions write call -> status update.

**Profile Service:**
- Integration: parser-originated suggestion draft persistence, review decisions, and apply flow.
- Integration: conflict resolution actions (`keep_existing`, `replace_existing`, `merge`, `add_separate`) and idempotent apply behavior.

**Gateway Service:**
- Integration: upload publishes parse request and returns `202` without blocking.

**Frontend:**
- Manual verification plus lint/build checks.
- Checklist:
  - [ ] Upload returns `202 Accepted` and does not block.
  - [ ] CV status changes from `pending` to `completed` (or `failed`) after processing.
  - [ ] Parsed suggestions are visible for review by section.
  - [ ] Accept/decline decisions are persisted and reflected in UI state.
  - [ ] Skip flow allows continuing onboarding and resuming review later.
  - [ ] Conflict suggestions require explicit resolution before apply.
  - [ ] Only accepted suggestions are applied to `GET /api/v1/profile`.
  - [ ] Failure scenarios show consistent parse status and error handling.

**CI:**
- Add parser unit and integration tests to push validation.
- Keep existing gateway/profile test coverage green.

## Done Criteria

- [ ] Local stack starts with parser included and healthy.
- [ ] CV upload triggers asynchronous parse via LocalStack queue.
- [ ] Successful parse writes suggestion drafts and marks CV as completed.
- [ ] User can accept/decline suggestions by section before persistence.
- [ ] User can skip and resume suggestion review later from profile.
- [ ] Canonical profile data changes only through explicit user acceptance.
- [ ] Skill overlap and experience timeline conflicts are resolved through explicit decision actions.
- [ ] Failed parse marks CV as failed with actionable error metadata.
- [ ] Profile read endpoints surface parsed results consistently.
- [ ] Parser, profile, and gateway test suites pass locally and in CI.