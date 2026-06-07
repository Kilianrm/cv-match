# Performance
## Purpose
Define practical performance targets, bottlenecks, and validation strategy for a portfolio-scale MVP of CV Match.
## Performance Goals
1. API responsiveness
- p95 read latency <= 500 ms.
- p95 write latency for enqueue workflows <= 800 ms.
- 5xx error rate < 1% in normal operation.
2. Asynchronous latency
- CV parsing p95 <= 45 seconds.
- Matching p95 <= 60 seconds.
- Upload accepted to first matches available p95 <= 2 minutes.
3. Queue health
- Age of oldest message < 120 seconds.
- Burst backlog drains within 10 minutes.
- DLQ steady-state target: 0 messages.
4. Reliability
- API monthly availability >= 99.5%.
- Worker success rate >= 99% (excluding malformed inputs and known permanent failures).
5. Cost guardrails
- Start with minimal baseline tasks.
- Scale on sustained pressure, not short spikes.
- Prioritize queue depth and message age over CPU-only scaling.

## Expected Load
Portfolio scope: validate architecture and operations, not high-scale production throughput.
1. Traffic assumptions
- Registered users: 100 to 500.
- Daily active users: 5% to 20%.
- Peak concurrent users: 5 to 20.
- API throughput: 0.5 to 3 req/s sustained, spikes up to 8 req/s.
2. Upload and parsing
- CV uploads/day: 5 to 30.
- Peak burst: 10 uploads in 10 minutes.
- Parser queue behavior: bursty with variable processing time.
3. Scraping
- Scheduled runs: 1 to 4 per day.
- One message per source per run.
- Scrape jobs/day: 5 to 30.
4. Matching
- User-scoped matching after parse or manual refresh.
- System-scoped matching after scrape windows.
- Match jobs/day: 20 to 200.
5. Notifications
- Digest emails/day: 20 to 300.
- Predictable spikes around digest schedules.

## Critical Paths
1. Upload to first visible matches
- API accepts upload -> parse queued -> parse completes -> match queued -> matches stored -> dashboard reads.
- Main bottlenecks: parser CPU, queue wait, matcher compute, DB writes.
2. Scrape to system rematch
- Scheduler triggers scrape -> offers persisted -> system match jobs queued -> rematch runs.
- Main bottlenecks: source variability, post-scrape queue concentration, heavy recomputation windows.
3. Dashboard/API reads
- Frontend requests matches -> API reads ranked data with pagination.
- Main bottlenecks: missing indexes, expensive sort/filter, oversized payloads.
4. Notification generation
- Triggered jobs -> eligible matches selected -> email sent -> delivery state recorded.
- Main bottlenecks: queue spikes, provider throttling, retry storms.
5. Retry and DLQ handling
- Worker failure -> backoff retry -> DLQ after max attempts -> triage and replay.
- Main bottlenecks: visibility timeout mismatch, non-idempotent processing, delayed DLQ response.
Priority in MVP:
- User experience first: upload-to-match and dashboard read paths.
- Stability second: scrape/rematch and retry/DLQ behavior.

## Scaling Assumptions
1. Baseline
- API: 1 task in dev/test, 2 tasks in production-like demos.
- Workers: 1 task per service minimum.
2. Signals
- API scales on sustained CPU/memory and request pressure.
- Workers scale on queue depth and age of oldest message.
- DLQ growth is a reliability alert, not a direct autoscaling trigger.
3. Worker autoscaling thresholds
- Scale out: queue depth per running task > 10 for 2+ minutes.
- Scale in: queue depth per running task < 2 for 10+ minutes.
- Parser and matcher scale independently.
4. Burst behavior
- Queues absorb short bursts.
- Temporary backlog is acceptable if it drains within target windows.
- Matcher post-scrape workloads may run in batches.
5. Re-evaluation triggers
- Reassess when latency, queue age, DLQ volume, or cost violates targets for multiple days.

## Database Performance Considerations
1. Workload profile
- Read-heavy: dashboard and profile reads.
- Write bursts: parser upserts, scraper upserts, matcher upserts.
2. Query and index priorities
- Index frequent joins and filters used by API and matcher.
- Prioritize match retrieval by user plus rank/recency.
- Avoid over-indexing low-value fields.
3. Write and contention controls
- Use idempotent upserts.
- Batch large recomputations.
- Keep transactions short.
4. Resource management
- Conservative connection pools.
- Query timeouts enabled.
- Monitor CPU, active connections, slow queries, and lock waits.
5. Escalation order
- Query plan and index tuning first.
- Pagination/payload optimization second.
- Selective caching third.
- Database tier scale-up or replicas last.

## Queue Throughput Considerations
1. Queue model
- One queue per worker domain.
- Small message payloads (IDs + metadata).
- At-least-once delivery; consumers must be idempotent.
2. Throughput goals
- Keep oldest message age within target.
- Drain burst backlogs in target windows.
- Avoid sustained growth across scheduler cycles.
3. Retry and visibility
- Visibility timeout > worst-case processing duration.
- Retries use exponential backoff with jitter.
- Bounded retries, then DLQ.
4. Consumer tuning
- Start low, increase concurrency gradually and per service.
- Prefer predictable, smaller batches for matcher and scraper spikes.
5. Required observability metrics
- queue_depth
- age_of_oldest_message_seconds
- processing_rate
- retry_rate
- dlq_messages_visible

## Load Testing Plan
1. Goals
- Validate latency and queue-drain targets.
- Identify first bottlenecks.
- Validate autoscaling behavior and alert usefulness.
2. Environment and data
- Use production-like staging topology.
- Use synthetic CVs with mixed complexity.
- Use representative offer volumes and source mix.
3. Core scenarios
- Read ramp for dashboard/profile API.
- Upload burst (10 in 10 minutes).
- Scrape burst followed by system matching.
- Notification window spike.
- Failure injection (DB/provider slowdown).
4. Success criteria
- Goals met for API latency, error rate, queue age, and drain time.
- End-to-end upload-to-first-match target met at p95.
- No uncontrolled retry amplification or prolonged DLQ accumulation.
5. Cadence and evidence
- Baseline tests before major changes.
- Targeted reruns after queue/matcher/parser/index changes.
- Monthly lightweight regression run with recorded metrics and action items.

## Cost and Performance Tradeoffs
1. Shared database in MVP
- Pro: faster delivery and debugging.
- Con: tighter coupling and possible contention.
2. Async-first workflows
- Pro: resilient API and burst absorption.
- Con: eventual consistency and delayed updates.
3. Low baseline capacity
- Pro: lower monthly cost.
- Con: slower reaction to sudden spikes.
4. Simple scaling policies
- Pro: easier to operate and explain.
- Con: less optimization headroom.
5. Tune before scale
- Pro: better engineering signal and cost efficiency.
- Con: requires recurring performance review discipline.
6. Portfolio acceptance rule
- Current tradeoffs are acceptable while goals are met and incidents are diagnosable.
