# Service Definition: API Service

## 1) Purpose

Primary responsibility:
The API Service is the public entry point for CV Match. It handles authentication, user profile queries, dashboard data retrieval, and command requests that trigger background workflows.

- Authentication and identity are delegated to Amazon Cognito, while the API remains responsible for application-specific user data and protected business operations.

Why this is a separate service:
The API should stay responsive and focused on request/response flows. Heavy operations (parsing, scraping, matching, notifications, AI optimization) run asynchronously in specialized services.

## 2) Inputs and Outputs

What it receives:

| Input | Format | Source | Example |
|-------|--------|--------|---------|
| Auth requests | JSON over HTTPS | Frontend client | {"email":"user@example.com","password":"***"} |
| CV upload request | multipart/form-data | Frontend client | file + user_id |
| Dashboard query | HTTPS GET | Frontend client | /matches?limit=20 |
| Optimization request | JSON over HTTPS | Frontend client | {"match_id":"m123"} |

What it produces:

| Output | Format | Destination | Example |
|--------|--------|-------------|---------|
| Auth/session response | JSON | Frontend client | {"token":"..."} |
| CV object stored | File object | S3 | s3://cv-match/cv/u1.pdf |
| Parse job event | JSON message | SQS | {"job_type":"parse_cv_requested","user_id":"u1","cv_id":"c1","s3_key":"cv/u1.pdf"} |
| Dashboard response | JSON | Frontend client | list of ranked matches |
| Async jobs | Queue messages | SQS | parse_cv_requested |
| Status/error logs | Structured logs | Loki / CloudWatch | request_id, status, latency |

## 3) Data Model

Own database: No

Shared database usage:
- Reads/writes users, profiles, preferences, and platform-specific user metadata.
- Authentication credentials are managed by Amazon Cognito, so passwords are not stored in the shared database.
- Reads matches and job records for dashboard responses.
- Stores optimization requests and status references.

Core tables touched:
- users
- profiles
- preferences
- matches
- optimization_requests

## 4) APIs

Primary endpoints (MVP):
- POST /auth/register
- POST /auth/login
- POST /auth/logout
- POST /cv/upload
- GET /profile
- GET /matches
- POST /matches/{id}/optimize-cv
- GET /notifications/preferences
- PUT /notifications/preferences

Authentication model:

- Amazon Cognito handles user registration, login, password reset, and token issuance.
- The API validates Cognito JWT tokens on protected endpoints.
- Applicaiton user records store the Cognito user id as the identity reference.


Queue messages published by API:
- parse_cv_requested
- scrape_jobs_requested
- run_matching_requested
- send_notification_requested
- optimize_cv_requested

## 5) Dependencies

| Dependency | Type | Why |
|-----------|------|-----|
| Shared PostgreSQL | Sync | Core product reads/writes for profiles, matches, preferences, and optimization recores |
| Amazon Cognito | Sync | User authentication, token issuance, and identity provider|
| SQS | Async | Trigger background workflows |
| S3 | Sync | Store and fetch CV files |
| Auth provider | Sync | User auth and token validation |
| Observability stack | Sync/Async | Logs, metrics, traces, alerts |

## 6) Error Handling

| Failure Scenario | Recovery Strategy |
|------------------|-------------------|
| Invalid input | Return 4xx with validation details |
| DB timeout | Retry with backoff, return 503 if exhausted |
| Queue publish failure | Retry, then return 503 with request_id |
| Downstream worker delayed | Return accepted status and expose async status endpoint |

## 7) Scaling

Expected load:
- Bursty interactive traffic from users viewing dashboard and submitting actions.

Scaling strategy:
- Horizontal scaling on ECS Fargate by CPU, memory, and request rate.
- Keep API stateless to scale safely.

Bottlenecks:
- DB connections under high read bursts.

Optimization ideas:
- Add read caching for hot dashboard queries.
- Tune DB indexes for profile and match lookups.

## 8) Deployment

Runtime target:
- ECS on Fargate behind ALB.

IaC:
- AWS CDK with TypeScript.

Key environment values:
- DATABASE_URL
- SQS_QUEUE_URL
- S3_BUCKET
- COGNITO_USER_POOL_ID
- COGNITO_APP_CLIENT_ID
- COGNITO_REGION
- JWT_ISSUER
- LOG_LEVEL

Secrets:
- DB credentials,  API keys via AWS Secrets Manager.

Security behavior:

- Protected endpoints require a valid JWT issued by Amazon Cognito
- The API verifies token signature, issuer,expiration, and required claims before a authorizing access

## 9) Monitoring

Logs:
- Structured JSON logs to Loki (with CloudWatch integration for AWS-native signals).

Metrics:
- request_count
- request_latency_ms (p50/p95/p99)
- error_rate
- queue_publish_failures

Tracing:
- OpenTelemetry traces exported to Tempo.

Alerts:
- API error rate > 5% for 5 minutes.
- p95 latency above threshold.
- queue publish failures above threshold.

## 10) Testing

Unit tests:
- Validation and request handlers.

Integration tests:
- API + DB + SQS + auth flow.

Contract tests:
- Endpoint request/response contract stability.

Load tests:
- Dashboard and auth endpoints under concurrent users.

## 11) Known Limitations

- Async job status detail is minimal in MVP.
- No advanced rate-limiting strategy in initial release.
- Limited caching strategy in phase one.

## 12) Open Questions

1. Should optimization requests return immediate partial feedback or only async status?
2. Do we need API versioning from day one (/v1) for future compatibility?
3. Which endpoints need stricter rate limits in MVP (auth, upload, optimize)?
