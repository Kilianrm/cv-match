# Service Definition: Job Scraper Service

## 1) Purpose

**Primary responsibility:**

The Job Scraper Service consumes scraping events, collects job offers from selected external sources, normalizes the data into a common schema, and stores it for matching.

Scraping is source-centric (global ingestion), not user-centric. User personalization is handled downstream by the Matching Service.

**Why this is a separate service:**

Scraping is network-heavy, source-dependent, and prone to external rate limits or layout changes. Keeping it asynchronous isolates source failures from core product flows, keeps the API responsive, and allows independent scaling based on scrape demand.

MVP acquisition policy:
- Prefer official platform APIs when available.
- If no API is available, use allowed feed/export options.
- Use web scraping only when terms permit it and technical stability is acceptable.

MVP scope delimitation:
- Start with a controlled list of 2-3 sources.
- Target a limited set of role families, seniority levels, and geographies.
- Keep source ingestion global; personalization happens in the Matching Service.

## 2) Inputs and Outputs

What it receives:

| Input | Format | Source | Example |
|-------|--------|--------|---------|
| Scrape event request | JSON message | SQS | {"event_type":"scrape_jobs_requested","event_version":"v1","source":"linkedin","requested_at":"2026-05-19T10:00:00Z","trace_id":"t-456"} |

Input scope note:
- Scrape events target sources and time windows, not individual users or CVs.

Typical event filters:
- source
- role_family
- seniority_scope
- location_scope
- posted_within_days

What it produces:

| Output | Format | Destination | Example |
|--------|--------|-------------|---------|
| Normalized job offers | SQL rows / JSON | Shared PostgreSQL | title, company, location, salary_range, required_skills, source_url |
| Success event | JSON message | SQS | {"event_type":"jobs_scraped","event_version":"v1","source":"linkedin","offers_count":120,"processed_at":"2026-05-19T10:01:40Z","trace_id":"t-456"} |
| Failure event | JSON message | SQS | {"event_type":"jobs_scrape_failed","event_version":"v1","source":"linkedin","error_code":"SOURCE_TIMEOUT","processed_at":"2026-05-19T10:00:40Z","trace_id":"t-456"} |
| Service logs | JSON | Loki / CloudWatch | source, duration_ms, offers_count, status |

## 3) Data Model

Own database: No

Shared database usage:
- Inserts normalized job offers collected from external sources.
- Updates existing offers when source data changes.
- Stores scrape run metadata for audits, retries, and source health tracking.

Core tables touched:
- job_offers
- scrape_runs

Writes/ownership boundaries:
- Job Scraper owns source ingestion fields, normalized job content, and scrape metadata.
- It must not modify user profile data, matching scores, or notification settings.
- Writes must be idempotent for repeated events targeting the same source and run window.
- Duplicate records should be resolved with upsert rules using source job identifiers when available.

## 4) APIs

External API endpoints:
- None in MVP (event-driven worker service)

## 5) Dependencies

| Dependency | Type | Why |
|-----------|------|-----|
| SQS | Async | Consume scrape_jobs_requested events and publish jobs_scraped / jobs_scrape_failed outcomes |
| External job platforms | Sync | Fetch job listings from selected sources |
| Shared PostgreSQL | Sync | Store normalized job offers and scrape run metadata |
| HTML parsing libraries | Sync | Parse and normalize source-specific page structures |
| Observability stack (Loki, CloudWatch, OpenTelemetry) | Sync/Async | Emit logs, metrics, traces, and alerts for scraper health and debugging |

## 6) Error Handling

| Failure Scenario | Recovery Strategy |
|------------------|-------------------|
| Source timeout or temporary network failure | Retry up to 3 attempts with exponential backoff and jitter, then publish jobs_scrape_failed |
| Source HTML structure changed | Mark scrape as failed for that source version, publish jobs_scrape_failed, and raise alert for parser update |
| DB write error | Retry up to 5 attempts; if still failing, send event to DLQ and publish jobs_scrape_failed |
| Rate limiting (HTTP 429) | Back off according to source policy and retry within max attempt window |
| Duplicate scrape event | Apply idempotent upsert rules and avoid duplicate job records |

## 7) Scaling

Expected load:
- Bursty load based on schedule windows and source response times.

Scaling strategy:
- ECS Fargate autoscaling based on queue depth and CPU utilization.
- Baseline capacity: min 1 task to keep event consumption active.
- Scale out: when queue depth per running task stays above 10 for 2 minutes.
- Scale in: when queue depth per running task stays below 2 for 10 minutes.

Bottlenecks:
- External source latency, rate limits, and HTML variability.

Operational guardrails:
- SQS visibility timeout must be greater than max expected scrape duration.
- DLQ depth is treated as a scaling and reliability signal for investigation.

## 8) Deployment

Runtime target:
- ECS Fargate worker service (no public endpoint), running in private subnets.
- Service consumes events from SQS and writes results to shared PostgreSQL.

IaC:
- AWS CDK with TypeScript.
- Infrastructure is defined in CDK for queue wiring, task definition, autoscaling, and IAM permissions.

Key environment values:
- SCRAPER_QUEUE_URL
- SCRAPER_DLQ_URL
- DATABASE_URL
- SCRAPER_SOURCES
- LOG_LEVEL

Runtime configuration:
- Enable graceful shutdown so in-flight processing completes before task stop.
- Set SQS visibility timeout above maximum expected scrape duration.
- Configure CloudWatch log driver and OpenTelemetry exporter from environment.

Secrets:
- DB credentials via AWS Secrets Manager.
- Task role grants least-privilege access to SQS and secret retrieval.

Release strategy:
- Rolling deployment with health checks and automatic rollback on failure.

## 9) Monitoring

Logs:
- Structured logs to Loki (CloudWatch integration for AWS signals).
- Each log entry includes trace_id, source, status, duration_ms, and offers_count.

Metrics:
- scraper_events_total
- scraper_success_rate
- scraper_duration_ms
- scraper_failures_total
- scraper_queue_depth
- scraper_dlq_depth
- scraper_offers_collected_total

Tracing:
- OpenTelemetry traces for source fetch, parse, normalize, and persist stages.

Alerts:
- Error rate > 5% over 5 minutes
- Queue depth > 100 for 10 minutes
- DLQ depth > 0 for 5 minutes
- p95 scrape duration > 60 seconds for 10 minutes

## 10) Testing

Unit tests:
- Source-specific extraction and normalization logic.

Integration tests:
- End-to-end flow: SQS -> source fetch -> scraper -> PostgreSQL.

Load tests:
- Burst scrape events and queue drain performance.

## 11) Known Limitations

- MVP supports only a controlled list of sources.
- Source layout changes may require frequent scraper updates.
- No browser-based rendering fallback in MVP for JS-heavy pages.

## 12) Open Questions

1. Which exact sources are included in MVP?
2. What freshness target is required for job offers (for example, every 6h or 24h)?
3. How should duplicate listings across different sources be merged?
