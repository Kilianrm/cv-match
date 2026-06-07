# Service Definition: Notification Service

## 1) Purpose

**Primary responsibility:**

The Notification Service consumes notification-triggering events, checks user delivery preferences, selects newly eligible matches, builds outbound messages, and sends the daily or event-driven digest to the user.

In MVP, the primary channel is email. The service is designed so additional channels such as push, SMS, or messaging apps can be added later without moving notification logic back into the API or Matcher services.

**Why this is a separate service:**

Notification delivery depends on external providers, retry rules, channel preferences, and delivery history. Keeping it asynchronous isolates provider failures from core product flows, prevents duplicate sends, and allows delivery logic to evolve independently of matching and API behavior.

## 2) Inputs and Outputs

What it receives:

| Input | Format | Source | Example |
|-------|--------|--------|---------|
| New matches event | JSON message | SQS | {"event_type":"new_matches_available","event_version":"v1","user_id":"u1","new_match_count":5,"processed_at":"2026-05-19T10:00:08Z","trace_id":"t-999"} |
| Scheduled digest trigger | JSON message | SQS via EventBridge | {"event_type":"send_digest_daily","event_version":"v1","scheduled_for":"2026-05-20T09:00:00Z","trace_id":"t-1000"} |

Supported trigger sources:
- Matching Service publishes `new_matches_available` when a user receives new or reactivated matches.
- EventBridge publishes scheduled digest triggers to support daily email delivery windows.
- API-managed preference updates are read from the shared database at send time rather than pushed directly into this service.

What it produces:

| Output | Format | Destination | Example |
|--------|--------|-------------|---------|
| Outbound email | Provider payload | SES | subject, recipient, digest summary, match links |
| Delivery record | SQL rows / JSON | Shared PostgreSQL | status, channel, sent_at, delivered_match_count |
| Success event | JSON message | SQS or internal event stream | {"event_type":"notification_sent","event_version":"v1","user_id":"u1","channel":"email","delivered_match_count":5,"processed_at":"2026-05-19T10:01:00Z","trace_id":"t-999"} |
| Failure event | JSON message | SQS | {"event_type":"notification_failed","event_version":"v1","user_id":"u1","channel":"email","error_code":"SES_TEMPORARY_FAILURE","processed_at":"2026-05-19T10:00:20Z","trace_id":"t-999"} |
| Service logs | JSON | Loki / CloudWatch | user_id, channel, match_count, template_id, status |

Output rules:
- Only matches that have not already been notified through the target channel should be included in a new delivery.
- A notification send must atomically record which match ids were included so retries do not resend the same jobs as new.
- If a user has notifications disabled, the event is consumed, recorded as skipped, and no provider call is made.

## 3) Data Model

Own database: No

Shared database usage:
- Reads user notification preferences and channel settings.
- Reads match records that are eligible for delivery and have not already been notified.
- Writes notification delivery history and per-match delivery markers.
- Stores send attempts for auditability, retries, and support investigation.

Core tables touched:
- users: read delivery identity and account status
- notification_preferences: read opt-in status, frequency, preferred send time, and channel settings
- matches: read eligible match records and update `last_notified_at`, `notification_status`, or equivalent delivery markers
- notification_runs: insert one record per processing attempt (trigger_type, status, duration, error_code)
- notification_deliveries: insert one row per outbound delivery with provider response metadata

Writes/ownership boundaries:
- Notification Service owns delivery status, send attempt metadata, provider response references, and per-channel notification timestamps.
- It must not change match scoring, profile data, source job content, or user authentication data.
- Writes must be idempotent for the same `(user_id, channel, delivery_window)` or event identity so retried sends do not create duplicates.
- The service should mark included matches as notified only after the provider accepts the outbound request.

## 4) APIs

External API endpoints:
- None in MVP (event-driven worker service)

Consumed queue messages:
- Queue name: notification jobs queue
- Message types:
	- `new_matches_available`
	- `send_digest_daily`

Canonical event shapes:

```json
{
	"event_type": "new_matches_available",
	"event_version": "v1",
	"user_id": "550e8400-e29b-41d4-a716-446655440000",
	"new_match_count": 5,
	"processed_at": "2026-05-19T10:00:08Z",
	"trace_id": "t-999"
}
```

```json
{
	"event_type": "send_digest_daily",
	"event_version": "v1",
	"scheduled_for": "2026-05-20T09:00:00Z",
	"trace_id": "t-1000"
}
```

Published events:
- `notification_sent`
- `notification_failed`
- `notification_skipped`

Eligibility rules for MVP:
- Deliver only matches whose lifecycle state is still active and user-visible.
- Exclude matches already marked as notified for the same channel.
- Respect user preferences such as enabled/disabled status and daily frequency.
- Prefer digest-style aggregation over sending one email per match.

## 5) Dependencies

| Dependency | Type | Why |
|-----------|------|-----|
| SQS | Async | Consume notification triggers and publish outcome events |
| Shared PostgreSQL | Sync | Read preferences and eligible matches, store delivery history and send state |
| Amazon SES | Sync | Send outbound email notifications in MVP |
| Match data produced by Matching Service | Sync via DB | Build digest content from newly eligible matches |
| Observability stack (Loki, CloudWatch, OpenTelemetry) | Sync/Async | Emit logs, metrics, traces, and alerts for delivery health and debugging |

## 6) Error Handling

| Failure Scenario | Recovery Strategy |
|------------------|-------------------|
| User has notifications disabled | Record `notification_skipped` and do not call the provider |
| No eligible unseen matches at send time | Complete successfully with zero sends and record a skip reason |
| Temporary DB read/write error | Retry up to 5 attempts with exponential backoff and jitter; if exhausted, send event to DLQ and publish `notification_failed` |
| SES temporary failure or throttle | Retry with provider-aware backoff; if exhausted, keep matches unmarked and publish `notification_failed` |
| Invalid or bounced email address | Mark delivery as permanently failed, suppress repeated retries, and raise a support or product signal |
| Duplicate notification trigger | Apply idempotent delivery checks and avoid resending already recorded match ids |
| Service crash after provider send but before DB write | Reconcile using provider message id or idempotency key before attempting resend |

## 7) Scaling

Expected load:
- Small but bursty batches after matcher publishes new matches.
- Daily spikes at scheduled digest times.

Scaling strategy:
- ECS Fargate autoscaling based on queue depth and CPU utilization.
- Baseline capacity: min 1 task to keep event consumption active.
- Scale out: when queue depth per running task stays above 10 for 2 minutes.
- Scale in: when queue depth per running task stays below 2 for 10 minutes.
- Batch digest generation by user to keep provider calls and DB writes bounded.

Bottlenecks:
- Email provider throughput quotas.
- Database queries that join delivery history, preferences, and unseen matches.
- Large scheduled digests if many users become eligible in the same window.

Optimization ideas:
- Precompute candidate digest sets from recent match changes.
- Limit each digest to top-N matches and include a link to view the full dashboard.
- Use provider templates to reduce render cost and standardize content.

Operational guardrails:
- SQS visibility timeout must exceed worst-case digest generation and provider send duration.
- DLQ depth and provider bounce rate are treated as operational reliability signals.

## 8) Deployment

Runtime target:
- ECS Fargate worker service (no public endpoint), running in private subnets.
- Service consumes events from SQS, reads from shared PostgreSQL, and sends via SES.

IaC:
- AWS CDK with TypeScript.
- Infrastructure is defined in CDK for queue wiring, task definition, autoscaling, IAM permissions, and SES integration.

Key environment values:
- NOTIFICATION_QUEUE_URL
- NOTIFICATION_DLQ_URL
- DATABASE_URL
- SES_FROM_EMAIL
- NOTIFICATION_CHANNELS_ENABLED
- DIGEST_MAX_MATCHES
- LOG_LEVEL

Runtime configuration:
- Enable graceful shutdown so in-flight sends complete before task stop.
- Set SQS visibility timeout above maximum expected digest generation duration.
- Configure CloudWatch log driver and OpenTelemetry exporter from environment.

Secrets:
- DB credentials via AWS Secrets Manager.
- Task role grants least-privilege access to SQS, SES send actions, database connectivity, and secret retrieval.

Release strategy:
- Rolling deployment with health checks and automatic rollback on failure.
- Email template changes should be versioned so delivery issues can be traced to a specific template revision.

## 9) Monitoring

Logs:
- Structured logs to Loki (CloudWatch integration for AWS signals).
- Each log entry includes trace_id, user_id, channel, delivery_window, matches_included, status, and provider_message_id when available.

Metrics:
- notification_events_total
- notification_success_rate
- notification_duration_ms
- notification_failures_total
- notification_queue_depth
- notification_dlq_depth
- notification_sent_total
- notification_skipped_total
- notification_bounce_total

Tracing:
- OpenTelemetry traces for preference lookup, eligible match query, template render, provider send, and delivery persistence stages.

Alerts:
- Error rate > 5% over 5 minutes
- Queue depth > 100 for 10 minutes
- DLQ depth > 0 for 5 minutes
- Provider bounce or rejection rate above threshold
- Zero successful notifications during expected daily digest windows

## 10) Testing

Unit tests:
- Delivery eligibility rules based on preferences and prior notification state.
- Digest composition and top-N selection logic.

Integration tests:
- End-to-end flow: SQS -> preference lookup -> unseen match query -> SES send -> PostgreSQL delivery persistence.
- Retry flow where a provider failure does not mark matches as notified.

Contract tests:
- Event payload compatibility for `new_matches_available` and `send_digest_daily`.
- Provider payload contract for the SES template input shape.

Load tests:
- Burst of event-driven notifications after a large matching run.
- Scheduled daily digest run across the MVP user base.

## 11) Known Limitations

- MVP supports email only; other notification channels are deferred.
- Digest personalization is limited to match selection and simple template fields.
- Deliverability management such as unsubscribe links, bounce handling automation, and suppression lists may need deeper work after MVP.
- If match deduplication upstream is weak, digests may still contain semantically similar jobs from different sources.

## 12) Open Questions

1. Should MVP send notifications immediately on `new_matches_available`, only on the daily schedule, or support both modes?
2. What exact preference model is needed in MVP: enabled flag only, daily/weekly frequency, or configurable send time per user?
3. How should bounced or repeatedly undeliverable emails affect future notification attempts for the same user?
