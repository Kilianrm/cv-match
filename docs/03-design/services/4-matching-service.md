# Service Definition: Matching Service

## 1) Purpose

**Primary responsibility:**

The Matching Service consumes matching requests, reads the normalized user profile and available job offers, computes a transparent fit score, ranks relevant opportunities, and stores the resulting matches for dashboard and notification use.

The service supports two operational scopes in MVP:
- user-scoped matching after a CV has been parsed or a user explicitly requests refreshed matches
- system-scoped rematching after new job offers are scraped

**Why this is a separate service:**

Matching is compute-heavy, depends on multiple upstream datasets, and can be triggered by several asynchronous events. Keeping it out of the API preserves low request latency, isolates scoring logic from transport concerns, and allows scaling independently based on queue depth and scoring volume.

## 2) Inputs and Outputs

What it receives:

| Input | Format | Source | Example |
|-------|--------|--------|---------|
| Match event request | JSON message | SQS | {"event_type":"match_jobs_requested","event_version":"v1","scope":"user","user_id":"u1","cv_id":"c1","requested_at":"2026-05-19T10:00:00Z","trace_id":"t-789"} |

Supported trigger sources:
- API Service publishes `match_jobs_requested` when a user requests matching or after upload workflow orchestration.
- CV Parser Service publishes `match_jobs_requested` after a successful `cv_parsed` result.
- Job Scraper Service publishes `match_jobs_requested` with `scope=system` after new offers are persisted.

Supported matching scopes:
- `scope=user`: recompute matches for one user using the latest parsed profile and eligible job set.
- `scope=system`: recompute matches for users affected by newly scraped or updated offers.

What it produces:

| Output | Format | Destination | Example |
|--------|--------|-------------|---------|
| Ranked matches | SQL rows / JSON | Shared PostgreSQL | score, rank_position, score_breakdown, matched_at |
| Success event | JSON message | SQS | {"event_type":"matching_completed","event_version":"v1","scope":"user","user_id":"u1","matches_created":18,"processed_at":"2026-05-19T10:00:08Z","trace_id":"t-789"} |
| Notification trigger | JSON message | SQS | {"event_type":"new_matches_available","event_version":"v1","user_id":"u1","new_match_count":5,"processed_at":"2026-05-19T10:00:08Z","trace_id":"t-789"} |
| Failure event | JSON message | SQS | {"event_type":"matching_failed","event_version":"v1","scope":"user","user_id":"u1","error_code":"PROFILE_NOT_FOUND","processed_at":"2026-05-19T10:00:03Z","trace_id":"t-789"} |
| Service logs | JSON | Loki / CloudWatch | user_id, scope, candidate_jobs, duration_ms, status |

Output rules:
- `new_matches_available` is published only when the run creates or refreshes matches that should surface to the user.
- Match storage must be deterministic for the same scoring inputs so retries do not create duplicate rows.
- A job can be matched many times during recomputation, but it must map to one persistent match record per `user_id + job_offer_id` so the system can tell whether the offer is new, already shown, already notified, dismissed, or applied.
- Notification and dashboard flows should treat only previously unseen or reactivated matches as new user-facing opportunities.

## 3) Data Model

Own database: No

Shared database usage:
- Reads normalized profile data required for scoring.
- Reads active job offers eligible for the target user or rematch window.
- Upserts ranked match records and stores score breakdowns for dashboard use.
- Stores match run metadata for observability, retries, and auditability.
- Tracks whether a matched offer has already been surfaced to the user so the same job is not repeatedly presented as new.

Core tables touched:
- profiles: read structured profile summary for matching
- profile_skills: read normalized user skill set
- job_offers: read active normalized offers and freshness metadata
- matches: upsert score, rank, match status, score breakdown, first_matched_at, last_matched_at, first_shown_at, last_notified_at, and user_action_state
- match_runs: insert one record per processing attempt (scope, status, duration, candidates_evaluated, error_code)

Writes/ownership boundaries:
- Matching Service owns scoring fields, ranking order, and match lifecycle fields.
- It must not modify CV parsing outputs, source job content, user account data, or notification preferences.
- Writes must be idempotent for the same `user_id + job_offer_id` identity, while storing the active `scoring_version` used for the latest evaluation.
- Repeated runs should update existing matches instead of inserting duplicates when the same offer remains eligible.
- Match lifecycle fields should support states such as `new`, `seen`, `notified`, `dismissed`, `applied`, and `expired`.
- The matcher must preserve `first_matched_at` and update `last_matched_at` on recomputation so downstream services can distinguish newly discovered matches from historical ones.

## 4) APIs

External API endpoints:
- None in MVP (event-driven worker service)

Consumed queue message:
- Queue name: matcher jobs queue
- Message type: `match_jobs_requested`

Canonical event shape:

```json
{
	"event_type": "match_jobs_requested",
	"event_version": "v1",
	"scope": "user",
	"user_id": "550e8400-e29b-41d4-a716-446655440000",
	"cv_id": "660e8400-e29b-41d4-a716-446655440111",
	"requested_at": "2026-05-19T10:00:00Z",
	"trace_id": "t-789",
	"triggered_by": "cv_parsed"
}
```

Published events:
- `matching_completed`
- `matching_failed`
- `new_matches_available`

Result classification rules:
- `new match`: first time a `(user_id, job_offer_id)` pair is stored.
- `existing active match`: a previously stored pair that is rescored and remains eligible.
- `reactivated match`: a previously expired or filtered-out pair that becomes eligible again after profile or job changes.
- Only `new match` and `reactivated match` results are eligible to trigger `new_matches_available`.

Scoring model for MVP:
- Skill overlap: 40%
- Seniority fit: 20%
- Domain or industry fit: 15%
- Location or remote compatibility: 15%
- Language fit: 10%

Final score formula:

```text
match_score = 0.4S + 0.2E + 0.15D + 0.15L + 0.1Lang
```

All component scores are normalized to the range `[0,1]` before aggregation.

## 5) Dependencies

| Dependency | Type | Why |
|-----------|------|-----|
| SQS | Async | Consume `match_jobs_requested` and publish outcome events |
| Shared PostgreSQL | Sync | Read profiles and job offers, store ranked matches and run metadata |
| Profile data produced by CV Parser | Sync via DB | Use normalized skills, experience, languages, and seniority for scoring |
| Job data produced by Job Scraper | Sync via DB | Use normalized offers and requirements as scoring candidates |
| Observability stack (Loki, CloudWatch, OpenTelemetry) | Sync/Async | Emit logs, metrics, traces, and alerts for scoring health and debugging |

## 6) Error Handling

| Failure Scenario | Recovery Strategy |
|------------------|-------------------|
| Profile not found for user-scoped run | Mark as failed without retry, publish `matching_failed`, and wait for upstream parsing completion |
| No active job offers available | Complete successfully with zero matches and do not publish `new_matches_available` |
| Temporary DB read/write error | Retry up to 5 attempts with exponential backoff and jitter; if exhausted, send event to DLQ and publish `matching_failed` |
| Duplicate match request | Apply idempotent run and upsert rules so repeated requests do not duplicate matches |
| Previously matched job appears again in recomputation | Update the existing match record, keep historical first-match metadata, and suppress duplicate "new" delivery |
| Unexpected scoring exception | Log stack trace, mark run failed, publish `matching_failed`, and allow queue retry subject to max attempts |
| Large system-scoped rematch exceeds time budget | Process in batches by affected user set or job window, checkpoint progress, and retry remaining work |

## 7) Scaling

Expected load:
- User-scoped bursts after CV uploads or manual refresh actions.
- System-scoped bursts after scraping windows complete and new offers are added.

Scaling strategy:
- ECS Fargate autoscaling based on queue depth and CPU utilization.
- Baseline capacity: min 1 task to keep event consumption active.
- Scale out: when queue depth per running task stays above 10 for 2 minutes.
- Scale in: when queue depth per running task stays below 2 for 10 minutes.
- For large rematch windows, split work into smaller batches to keep task duration predictable.

Bottlenecks:
- Candidate-job fanout for users with broad eligibility.
- Database query cost when reading many active offers.
- Recomputing scores for system-wide refreshes after large scrape runs.

Optimization ideas:
- Pre-filter candidate jobs by freshness, location scope, and coarse seniority before full scoring.
- Cache normalized scoring features per job offer.
- Limit notification-triggering output to top-N newly relevant matches.
- Query candidate jobs with a left join to existing matches so scoring can cheaply detect first-time versus already-known offers.

Operational guardrails:
- SQS visibility timeout must exceed worst-case batch scoring duration.
- DLQ depth is treated as a reliability signal requiring investigation.

## 8) Deployment

Runtime target:
- ECS Fargate worker service (no public endpoint), running in private subnets.
- Service consumes events from SQS and writes results to shared PostgreSQL.

IaC:
- AWS CDK with TypeScript.
- Infrastructure is defined in CDK for queue wiring, task definition, autoscaling, and IAM permissions.

Key environment values:
- MATCHER_QUEUE_URL
- MATCHER_DLQ_URL
- NOTIFICATION_QUEUE_URL
- DATABASE_URL
- MATCH_SCORING_VERSION
- MATCH_TOP_N_DEFAULT
- LOG_LEVEL

Runtime configuration:
- Enable graceful shutdown so in-flight scoring completes before task stop.
- Set SQS visibility timeout above maximum expected scoring duration.
- Configure CloudWatch log driver and OpenTelemetry exporter from environment.

Secrets:
- DB credentials via AWS Secrets Manager.
- Task role grants least-privilege access to SQS, database connectivity, and secret retrieval.

Release strategy:
- Rolling deployment with health checks and automatic rollback on failure.
- Changes to scoring logic must advance `MATCH_SCORING_VERSION` so recalculations remain traceable.

## 9) Monitoring

Logs:
- Structured logs to Loki (CloudWatch integration for AWS signals).
- Each log entry includes trace_id, scope, candidates_evaluated, matches_written, status, and duration_ms.

Metrics:
- matcher_events_total
- matcher_success_rate
- matcher_duration_ms
- matcher_failures_total
- matcher_queue_depth
- matcher_dlq_depth
- matcher_candidates_evaluated_total
- matcher_matches_created_total

Tracing:
- OpenTelemetry traces for candidate fetch, feature scoring, rank calculation, persistence, and event publication stages.

Alerts:
- Error rate > 5% over 5 minutes
- Queue depth > 100 for 10 minutes
- DLQ depth > 0 for 5 minutes
- p95 match duration > 60 seconds for 10 minutes
- Zero successful matcher runs during expected scrape windows

## 10) Testing

Unit tests:
- Scoring component logic for skills, seniority, domain, location, and language.
- Rank ordering and tie-break behavior.

Integration tests:
- End-to-end flow: SQS -> profile/job fetch -> score computation -> PostgreSQL -> notification event publication.
- Recompute an existing `(user_id, job_offer_id)` pair and verify that the system updates the existing record rather than creating a duplicate.

Contract tests:
- Event payload compatibility for `match_jobs_requested` and `new_matches_available`.

Load tests:
- Burst user-scoped match requests after mass CV uploads.
- Batch rematching after a large scrape event.

## 11) Known Limitations

- MVP scoring is rule-based and intentionally simple; it does not use learned ranking models.
- Explainability is limited to a stored score breakdown rather than full narrative explanations.
- Cross-source duplicate job consolidation may reduce score quality until a stronger deduplication strategy is added.
- System-scoped rematching may need batching safeguards if the active user and job inventory grows quickly.
- If job sources publish the same opening under different identifiers, duplicate suppression depends on upstream deduplication quality in `job_offers`.

## 12) Open Questions

1. What threshold should define a match as notification-worthy in MVP?
2. Should low-scoring historical matches be soft-deactivated or kept indefinitely for analytics?
3. How often should a full system-wide rematch run in addition to event-triggered recomputation?
