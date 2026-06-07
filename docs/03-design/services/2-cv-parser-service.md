# Service Definition: CV Parser Service

## 1) Purpose

**Primary responsibility:**

The CV Parser Service processes uploaded CV PDFs and extracts structured profile data (skills, experience, education, languages, seniority) for matching.

The CV Parser Service consumes CV parsing events, retrieves the target PDF, extracts and normalizes profile data ( skills,experiencie,education,languages, and seniority, and persistes the structured result for matching).

**Why this is a separate service:**

Parsing is CPU-intensive and failure-prone. Running it asynchronously keeps the API responsive and isolates parsing errors.
PDF parsing is CPU-intensive and format-sensitive, keeping it as an isolated worker preservers API responsiveness, improves fault isolation, and allows independent scaling based on parsing demand.


## 2) Inputs and Outputs

What it receives:

| Input | Format | Source | Example |
|-------|--------|--------|---------|
| Parse event request | JSON message | SQS | {"event_type":"parse_cv_requested",event_version":"v1","user_id":"u1","cv_id":"c1","requestesd_at":"2026-05-19T10:00:00Z","trace_id":"t-123"} |

Key derivation rule:
- `s3_key` is derived from message fields as `cv/{user_id}/{cv_id}.pdf`.
- This keeps the event payload compact and avoids duplicated path data.

What it produces:

| Output | Format | Destination | Example |
|--------|--------|-------------|---------|
| Parsed profile fields | SQL rows / JSON | Shared PostgreSQL | skills, experience, education, seniority |
| Success event | JSON message | SQS | {"event_type":"cv_parsed","event_version":"v1","user_id":"u1","cv_id":"c1","processed_at":"2026-05-19T10:00:04Z","trace_id":"t-123"} |
| Failure event | JSON message | SQS | {"event_type":"cv_parse_failed","event_version":"v1","user_id":"u1","cv_id":"c1","error_code":"UNSUPPORTED_PDF","processed_at":"2026-05-19T10:00:03Z","trace_id":"t-123"} |
| Service logs | JSON | Loki / CloudWatch | parse_time_ms, status, confidence |

## 3) Data Model

Own database: No

Shared database usage:
- Writes CV metadata required for parsing context.
- Writes normalized profile data extracted from the CV.
- Updates parsing status and timestamps for processing lifecycle tracking.
- Stores parse execution metadata for audit and retry analysis.

Core tables touched:

- cvs: read CV metadata and update parsing status (pending, parsed,failed)
- profiles: upsert normalized profile summary fields
- profile_skills: upsert normalized skills linked to profile
- parse_runs: insert one record per processing attempt (status,duration,error_code,confidence)

Writes/ownership boundaries:

- CV Parser owns only parsing-realted fileds and status transitions
- It must not modify user account data or non-parsing business attributes.
- Writes must be idempotent for repeated parsing events on the same user_id + cv_id.

## 4) APIs

External API endpoints:
- None in MVP (event-driven worker service)

## 5) Dependencies

| Dependency | Type | Why |
|-----------|------|-----|
| SQS | Async |Consume parse_cv_requested |
| S3 | Sync | Retrieve uploaded CV PDFs for parsing |
| Shared PostgreSQL | Sync | Store normalized profile data, parsing status, and parse run metadata |
| PDF parsing libraries | Sync | Extract and normalize structured data from PDF documents |
| Observability stack (Loki,CloudWatch,OpenTelemetry) | Sync/Async | Emit logs, metrics, traces, and alerts for parser health and debugging |

## 6) Error Handling

| Failure Scenario | Recovery Strategy |
|------------------|-------------------|
| Corrupted or unsupported PDF | Mark as permanent failure, update parse status to failed, and publish cv_parse_failed |
| Temporary S3 access error | Retry up to 3 attempts with exponential backoff and jitter, then publish cv_parse_failed |
| DB write error | Retry up to 5 attempts; if still failing, send event to DLQ and publish cv_parse_failed |
| Unexpected parser exception | Log stack trace, mark processing as failed, and publish cv_parse_failed |
| Duplicate parsing event | Apply idempotent write rules and return success without duplicating profile records |

## 7) Scaling

Expected load:
- Bursty traffic after CV upload peaks, with uneven PDF complexity.

Scaling strategy:
- ECS Fargate autoscaling based on queue depth and CPU utilization.
- Baseline capacity: min 1 task to keep event consumption active.
- Scale out: when queue depth per running task stays above 10 for 2 minutes.
- Scale in: when queue depth per running task stays below 2 for 10 minutes.
- Protect queue latency by prioritizing queue depth signals over CPU-only signals.

Bottlenecks:
- CPU-heavy parsing and PDF format variability.

Operational guardrails:
- SQS visibility timeout must be greater than the maximum expected parse duration.
- DLQ depth is treated as a scaling and reliability signal for investigation.

## 8) Deployment

Runtime target:
- ECS Fargate worker service (no public endpoint), running in private subnets.
- Service consumes events from SQS and writes results to shared PostgreSQL.

IaC:
- AWS CDK with TypeScript.

Key environment values:
- PARSER_QUEUE_URL
- PARSER_DLQ_URL
- S3_BUCKET
- DATABASE_URL
- LOG_LEVEL

Runtime configuration:
- Enable graceful shutdown so in-flight processing completes before task stop.
- Set SQS visibility timeout above maximum expected parse duration.
- Configure CloudWatch log driver and OpenTelemetry exporter from environment.

Secrets:
- DB credentials via AWS Secrets Manager.
- Task role grants least-privilege access to SQS, S3 object read, and secret retrieval.

Release strategy:
- Rolling deployment with health checks and automatic rollback on failure.

## 9) Monitoring

Logs:
- Structured logs to Loki (CloudWatch integration for AWS signals).

Metrics:
- parser_events_total
- parser_success_rate
- parser_duration_ms
- parser_failures_total
- parser_queue_depth
- parser_dlq_depth

Tracing:
- OpenTelemetry traces for parse pipeline stages.

Alerts:
- Error rate > 5% over 5 minutes
- Queue depth > 100 for 10 minutes
- DLQ depth > 0 for 5 minutes
- p95 parse duration > 45 seconds for 10 minutes

## 10) Testing

Unit tests:
- Field extraction and normalization logic.

Integration tests:
- End-to-end flow: SQS -> S3 -> parser -> PostgreSQL.

Load tests:
- Burst uploads and queue drain performance.

## 11) Known Limitations

- No OCR fallback in MVP for scanned image-only PDFs.
- Limited multilingual parsing support in MVP.