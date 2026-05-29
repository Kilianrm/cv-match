# Observability

## Purpose

Describe logs, metrics, traces, dashboards, and alerting for CV Match.

This document owns detailed observability standards and operational practices.

## Observability Baseline Stack

To avoid losing important context moved from other architecture sections, this document is the source of truth for the observability stack used in MVP.

Baseline components:
- Logs: structured application logs centralized in Grafana Loki
- Metrics: Prometheus metrics for services, queues, and core infrastructure signals
- Tracing: OpenTelemetry instrumentation with traces stored in Tempo
- AWS signals: CloudWatch remains enabled for ECS, ALB, SQS, and Aurora infrastructure health
- Dashboards: Grafana dashboards combining logs, metrics, and traces for triage
- Alerting: Grafana Alerting plus CloudWatch alarms for critical infrastructure events

Correlation baseline:
- Cross-service correlation uses shared identifiers (service_name, environment, trace_id, job_id where applicable).
- Detailed propagation and field rules are defined in Trace Propagation and Logging Standards.

## Observability Goals

CV Match observability goals for MVP:

1. Fast incident detection
- Detect service degradation quickly (API errors, worker failures, queue backlog growth).
- Reduce mean time to detect (MTTD) using actionable alerts.

2. End-to-end traceability
- Correlate API requests with asynchronous jobs across parser, scraper, matcher, and notification flows.
- Preserve trace_id and trigger metadata across queue boundaries.

3. Reliable operational signals
- Prioritize golden signals (latency, traffic, errors, saturation) for API and workers.
- Track queue-specific health (depth, age of oldest message, DLQ activity).

4. Low-noise alerting
- Alert only on conditions that require action.
- Reduce non-actionable alarms through thresholds and short stabilization windows.

5. Cost-aware monitoring
- Start with essential dashboards and alerts for MVP.
- Expand instrumentation only when it improves incident response or release confidence.

## Logging Standards

Logging standards define what every service must emit so incidents can be diagnosed quickly.

Format and transport:
- Use structured JSON logs in all services (API and workers).
- Write logs to stdout/stderr in containers; centralize collection in the observability stack.
- Use consistent timestamp format (UTC ISO-8601).

Required log fields (minimum):
- timestamp
- level (debug, info, warn, error)
- service_name
- environment
- message
- trace_id
- request_id (for synchronous HTTP flows)
- job_id (for async worker flows, when available)

Correlation rules:
- Include trace_id in every log event and add request_id or job_id when applicable.
- Include queue message identifiers in worker-processing logs.
- Emit start/end log entries for long-running jobs with duration_ms.
- End-to-end propagation behavior is defined in Trace Propagation.

Severity usage:
- debug: development-only diagnostics; disable by default in production-like environments.
- info: normal lifecycle events (request handled, job completed).
- warn: recoverable anomalies (retries, timeouts, fallback paths).
- error: failed operations requiring investigation.

Privacy and security:
- Never log secrets, tokens, passwords, or raw credential material.
- Avoid logging full CV content or sensitive personal data.
- Mask or hash user identifiers when full values are not operationally required.

Retention and cost control (MVP):
- Keep high-cardinality fields limited.
- Use shorter retention for verbose logs and longer retention for error/audit-relevant logs.
- Review log volume periodically to control storage and ingestion cost.

## Metrics Standards

Metrics standards define which signals are mandatory, how they are labeled, and how they are used for alerts.

Metric design principles:
- Prefer low-cardinality labels to keep cost and query performance under control.
- Track service-level golden signals first: latency, traffic, errors, saturation.
- Add business/domain metrics only when they support operational decisions.

Required labels (minimum):
- service_name
- environment
- operation (endpoint or job type)
- status (success, error, retry where applicable)

API minimum metric set:
- request_count_total by endpoint and status class
- request_latency_ms (p50, p95, p99)
- error_rate_percent (4xx and 5xx tracked separately)
- in_flight_requests

Worker minimum metric set:
- jobs_processed_total by job_type and outcome
- job_duration_ms by job_type
- retries_total by job_type
- job_failures_total by error category

Queue-related minimum metric set:
- queue_depth
- age_of_oldest_message_seconds
- dlq_messages_visible
- processing_lag_seconds (enqueue to completion)

Infrastructure support metrics:
- ECS task health and restart count
- Aurora CPU, connections, and storage pressure
- ALB target health and 5xx responses

Collection and aggregation:
- Scrape/collect at intervals appropriate for MVP incident response.
- Retain high-resolution data for short windows and aggregate for long-term trend analysis.
- Keep metric naming consistent across services to enable shared dashboards.

Alert mapping rule:
- Every critical alert must map to at least one documented metric and one runbook action.

## Trace Propagation

Trace propagation rules ensure one request can be followed across synchronous and asynchronous boundaries.

Propagation standard:
- Generate or accept trace context at API ingress.
- Propagate trace context in internal HTTP calls and queue messages.
- Include trace_id in all logs, key metrics labels, and error events.

Async propagation requirements:
- Every queue message must include trace_id and trigger metadata.
- Workers must continue the same trace when processing the message.
- Retries must preserve original trace_id and add retry counters as metadata.

Minimum tracing spans:
- API request span (ingress to response)
- Queue publish span
- Worker processing span
- External dependency spans (database, storage, auth provider, email provider)

Sampling policy (MVP):
- Keep low-overhead default sampling for normal traffic.
- Increase sampling dynamically during incidents or debugging sessions.

## Dashboards

Dashboards should support fast triage by role and by failure domain.

Minimum dashboard set:
- Platform overview: request rate, error rate, latency, saturation, deployment markers.
- API dashboard: endpoint latency/error distribution and auth failure trends.
- Worker dashboard: job throughput, processing time, retries, failures by job type.
- Queue dashboard: queue depth, age of oldest message, DLQ volume, backlog trend.
- Infrastructure dashboard: ECS task health, ALB 5xx, Aurora pressure signals.

Dashboard rules:
- Use consistent filters: environment, service_name, operation.
- Surface p95/p99 latency, not only averages.
- Include links from dashboard panels to related logs and traces.
- Keep a separate incident dashboard optimized for active troubleshooting.

## Alerting Rules

Alerts must be actionable, scoped, and tied to response steps.

Severity model:
- Critical: immediate user impact or sustained system failure.
- High: degraded service quality needing prompt intervention.
- Warning: early signal requiring investigation during business hours.

MVP critical alerts:
- API 5xx error rate above threshold for sustained window.
- API p95 latency above threshold for sustained window.
- Queue age of oldest message above threshold.
- DLQ messages visible above zero for sustained window.
- Worker failure rate above threshold.

Alert quality rules:
- Use stabilization windows to avoid flapping.
- Deduplicate related alerts into one incident signal.
- Each alert must include: impact, likely causes, first response actions, dashboard/runbook links.
- Review alert effectiveness monthly and tune noisy alerts.

## Queue and Worker Monitoring

Queue and worker monitoring focuses on throughput, lag, and failure isolation.

Monitoring execution model:
- Use Metrics Standards as the source of truth for queue/worker metric definitions.
- Use Alerting Rules as the source of truth for severity and threshold behavior.

Operational monitoring priorities:
- Detect backlog growth early and identify which worker type is the bottleneck.
- Differentiate transient retry bursts from sustained failure patterns.
- Track worker health degradation (restarts/crash loops) before job loss occurs.
- Monitor DLQ accumulation and replay progress during recovery.

Recovery practices:
- Pause/limit producers if downstream queue pressure is unsafe.
- Use controlled DLQ replay after root cause mitigation.
- Validate idempotency before replaying failed messages.

## Operational Runbooks

Runbooks provide step-by-step operational response for recurring incidents.

Minimum runbook catalog:
- High API error rate
- High API latency
- Queue backlog spike
- DLQ growth
- Worker crash loop or repeated job failures
- Missing logs/metrics/traces from one service

Runbook template (required fields):
- Trigger condition and alert source
- Immediate impact and risk
- First 5-minute checks
- Deeper diagnostics path
- Mitigation and rollback options
- Exit criteria and post-incident notes

Ownership and maintenance:
- Assign an owner per runbook.
- Validate runbooks after major architecture/deployment changes.
- Capture lessons learned and update runbooks after each real incident.
