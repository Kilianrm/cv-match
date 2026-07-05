# Service Definition: CV Parser Service

## 1) Purpose

Primary responsibility:

The CV Parser Service consumes asynchronous parse events, reads uploaded CV files, and extracts normalized profile suggestions.

Why this is a separate service:

- Parsing is CPU-intensive and format-sensitive.
- Event-driven isolation keeps API latency low and failures contained.
- Parser scaling can follow queue pressure independently from API traffic.

## 2) Inputs and Outputs

What it receives:

| Input | Format | Source | Example |
|-------|--------|--------|---------|
| Parse event request | JSON message | SQS | {"event_type":"parse_cv_requested","event_version":"v1","user_id":"u1","cv_id":"c1","requested_at":"2026-05-19T10:00:00Z","trace_id":"t-123"} |

Key derivation rule:
- `s3_key` is derived as `cv/{user_id}/{cv_id}.pdf`.

What it produces:

| Output | Format | Destination | Example |
|--------|--------|-------------|---------|
| Parsed suggestion payload | JSON HTTP payload | Profile Service internal endpoint | suggested skills, experience, education, certifications, and basic profile fields |
| Success event | JSON message | SQS | {"event_type":"cv_parsed","event_version":"v1","user_id":"u1","cv_id":"c1","processed_at":"2026-05-19T10:00:04Z","trace_id":"t-123"} |
| Failure event | JSON message | SQS | {"event_type":"cv_parse_failed","event_version":"v1","user_id":"u1","cv_id":"c1","error_code":"UNSUPPORTED_PDF","processed_at":"2026-05-19T10:00:03Z","trace_id":"t-123"} |
| Service logs | JSON | CloudWatch Logs | parse_time_ms, status, confidence |

Important behavior:
- CV Parser does not directly write canonical profile tables.
- Parsed output is saved as reviewable suggestions by Profile Service.
- Profile changes require explicit user acceptance in the frontend workflow.

## 3) Data Model

Own database: No

Direct table ownership:
- None.

Persistence model:
- Profile Service owns persistence for suggestion drafts and canonical profile entities.
- Parser sends idempotent suggestion payloads keyed by `user_id + cv_id`.

Write boundaries:
- Parser owns extraction and normalization quality.
- Parser does not decide final profile values.

## 4) APIs

External API endpoints:
- None (event-driven worker service).

Internal integration:
- `POST /internal/users/{user_id}/parse-suggestions`
- `GET /health`

## 5) Dependencies

| Dependency | Type | Why |
|-----------|------|-----|
| SQS | Async | Consume `parse_cv_requested` |
| S3 | Sync | Retrieve uploaded CV documents |
| Profile Service | Sync | Persist parsed suggestions for user review |
| PDF parsing libraries | Sync | Extract and normalize structured profile data |
| Observability stack (CloudWatch only) | Sync/Async | Emit logs, metrics, and alarms |

## 6) Error Handling

| Failure Scenario | Recovery Strategy |
|------------------|-------------------|
| Corrupted or unsupported PDF | Mark parse as failed, publish `cv_parse_failed`, keep previous profile unchanged |
| Temporary S3 access error | Retry up to 3 attempts with exponential backoff and jitter, then fail |
| Profile Service write error | Retry up to 5 attempts; if exhausted, send to DLQ and publish `cv_parse_failed` |
| Unexpected parser exception | Log stack trace, mark processing as failed, and publish `cv_parse_failed` |
| Duplicate parsing event | Apply idempotent payload semantics and avoid duplicate suggestion batches |

## 7) Scaling

Expected load:
- Bursty traffic after CV uploads with uneven parsing duration per file.

Scaling strategy:
- ECS Fargate autoscaling based on queue depth and CPU.
- Baseline capacity: min 1 task.
- Scale out: queue depth per task > 10 for 2 minutes.
- Scale in: queue depth per task < 2 for 10 minutes.

Operational guardrails:
- SQS visibility timeout must exceed max parse duration.
- DLQ depth is a reliability trigger for investigation.

## 8) Deployment

Runtime target:
- ECS Fargate worker service (no public endpoint), running in private subnets.

IaC:
- AWS CDK with TypeScript.

Key environment values:
- PARSER_QUEUE_URL
- PARSER_DLQ_URL
- S3_BUCKET
- PROFILE_SERVICE_BASE_URL
- LOG_LEVEL

Runtime configuration:
- Graceful shutdown for in-flight parse completion.
- Structured logs with trace correlation.

Secrets and IAM:
- Task role has least-privilege access to SQS and S3.
- Internal service auth follows platform internal trust model.

## 9) Monitoring

Observability baseline:
- CloudWatch Logs for structured parser logs.
- CloudWatch Metrics (custom + AWS managed) for parser health.
- CloudWatch Alarms for failure and backlog thresholds.

Metrics:
- parser_events_total
- parser_success_rate
- parser_duration_ms
- parser_failures_total
- parser_queue_depth
- parser_dlq_depth
- parser_suggestions_generated_total

Alerts:
- Error rate > 5% over 5 minutes
- Queue depth > 100 for 10 minutes
- DLQ depth > 0 for 5 minutes
- p95 parse duration > 45 seconds for 10 minutes

## 10) Testing

Unit tests:
- Field extraction and normalization logic.
- Confidence scoring and section mapping.

Integration tests:
- End-to-end flow: SQS -> S3 -> parser -> Profile suggestions endpoint.
- Idempotency checks for duplicate parse events.

Load tests:
- Burst uploads and queue drain behavior.

## 11) Parsing Core Implementation Plan (MVP)

Recommended approach:
- Use a hybrid parser pipeline (deterministic extraction + LLM structuring), not LLM-only.
- Deterministic steps handle stable fields (emails, phones, dates, links, obvious headers).
- LLM step maps segmented CV text into the profile suggestion template.

Parser pipeline stages:
1. File validation: extension, MIME type, size, and basic corruption checks.
2. Text extraction: extract raw text from PDF pages and preserve reading order heuristics.
3. Section segmentation: detect candidate blocks (`basic_info`, `skills`, `experience`, `education`, `certifications`).
4. Deterministic extraction: parse straightforward fields with rule-based logic.
5. LLM structuring: transform extracted/segmented text into typed section payloads.
6. Normalization: normalize labels, dates, and catalog candidates.
7. Confidence scoring: assign per-item confidence to support review UX.
8. Payload assembly: produce `parse_suggestion_items`-compatible output (`section`, `item_key`, `proposed_payload`, `confidence`, `is_conflict`).

### Template Output Contract

The parser should output a strict JSON structure aligned with profile sections:
- `basic_info`
- `location`
- `skills`
- `preferred_roles`
- `experience`
- `education`
- `certifications`

Contract rules:
- Output must be schema-valid JSON.
- Unknown fields are dropped before persistence.
- Invalid items are flagged for review or rejected by validation.
- Each suggestion item must map to one section and one stable `item_key`.

### LLM Runtime Strategy (Local -> ECS)

Local development:
- Run inference in a local containerized runtime (for example Ollama or vLLM) on the Docker network.
- CV Parser calls the local inference endpoint through an internal HTTP client.

Cloud deployment (AWS ECS):
- Keep CV Parser as a stateless worker service.
- Deploy inference either:
	- as a sidecar in the same task (simple start), or
	- as a separate internal inference service (better independent scaling).
- Use the same prompt and schema contract between local and ECS environments.

Model selection guidance for MVP:
- Start with one instruction model that performs reliable JSON extraction.
- Prefer smaller models first for latency and cost control.
- Tune prompts and validations before increasing model size.

Environment values for LLM integration (in addition to current parser env):
- `LLM_BASE_URL`
- `LLM_MODEL_NAME`
- `LLM_TIMEOUT_MS`
- `LLM_MAX_RETRIES`

MVP quality goals:
- Prioritize precision over recall for auto-suggested structured fields.
- Emit fewer but higher-confidence suggestions when text is ambiguous.
- Mark uncertain extractions as conflicts or low-confidence review items.

Out-of-scope for MVP:
- OCR for scanned image-only CVs.
- Advanced multilingual parsing beyond baseline normalization.
- ML model fine-tuning loops.

## 12) Known Limitations

- No OCR fallback in MVP for scanned image-only PDFs.
- Limited multilingual parsing support in MVP.
- Suggestion confidence calibration starts with conservative defaults and improves with feedback.
