# API Specification

## Purpose

Define the external API contract for CV Match.

## Base Information

- Base URL: `/api`
- Versioning strategy: `/v1` path prefix
- Authentication model: Amazon Cognito JWT bearer tokens for protected endpoints
- Full URL template: `https://<host>/api/v<version>/{endpoint}`

## Endpoint Tree Map

```text
/api/v1
|-- /auth
|   |-- POST /auth/register
|   |-- POST /auth/login
|   `-- POST /auth/logout
|-- /cv
|   |-- POST /cv/upload
|   `-- GET /cv/current
|-- /profile
|   `-- GET /profile
|-- /matches
|   |-- GET /matches
|   |-- POST /matches/{id}/optimize-cv
|   `-- GET /matches/{id}/optimized-cv
|-- /optimizations
|   `-- GET /optimizations/{optimization_request_id}/status
`-- /notifications/preferences
	|-- GET /notifications/preferences
	`-- PUT /notifications/preferences
```

## Endpoints

### Auth

#### POST /auth/register

- Purpose: Register a new user in Cognito, then create and link the application user record in the database..
- Auth: Public endpoint (no JWT required).
- Request:
	- Headers: `Content-Type: application/json`
	- Body: `email` (required), `password` (required)
- Success responses: `201 Created`
- Error responses: `400 Bad Request`, `409 Conflict`, `429 Too Many Requests`, `500 Internal Server Error`

Request example:
```json
{
	"email": "user@example.com",
	"password": "StrongPass123!",
	"full_name": "Jane Doe"
}
```

Success response example:
```json
{
	"user_id": "u1",
	"cognito_user_id": "0f3f3b1a-2a4b-4f0b-9f4a-1dc3e7f4a9f2",
	"status": "registered",
	"message": "User registered successfully"
}
```

#### POST /auth/login

- Purpose: Authenticate a user and return a session token set.
- Auth: Public endpoint (no JWT required).
- Request:
	- Headers: `Content-Type: application/json`
	- Body: `email` (required), `password` (required)
- Success responses: `200 OK`
- Error responses: `400 Bad Request`, `401 Unauthorized`, `429 Too Many Requests`, `500 Internal Server Error`

Request example:
```json
{
	"email": "user@example.com",
	"password": "StrongPass123!"
}
```

Success response example:
```json
{
	"access_token": "eyJ...",
	"refresh_token": "eyJ...",
	"expires_in": 3600,
	"token_type": "Bearer"
}
```

#### POST /auth/logout

- Purpose: Invalidate the current session token.
- Auth: Protected endpoint (Bearer JWT required).
- Request:
	- Headers: `Authorization: Bearer <token>`
- Success responses: `204 No Content`
- Error responses: `401 Unauthorized`, `500 Internal Server Error`


### CV Management

#### POST /cv/upload

- Purpose: Upload a CV file and trigger asynchronous parsing.
- Auth: Protected endpoint (Bearer JWT required).
- Request:
	- Headers: `Authorization: Bearer <token>`, `Content-Type: multipart/form-data`
	- Body: `file` (required)
	- Constraints: PDF or DOCX, max size 5 MB
- Success responses: `202 Accepted`
- Error responses: `400 Bad Request`, `401 Unauthorized`, `413 Payload Too Large`, `422 Unprocessable Content`, `500 Internal Server Error`
- Async message published: [parse_cv_requested](services/api-service.md)

Notes:
- The `file` field is sent as a multipart form part (raw file bytes), not as JSON text.
- The endpoint returns `202 Accepted` once the file is validated and queued for async parsing.
- `422 Unprocessable Content` is only for immediate pre-queue validation failures (for example, corrupted or unsupported files).
- Parse-quality failures detected during async processing are reported through async job status/results, not from the upload request.

Request example:
```json
{
	"file": "<raw bytes of candidate_cv.pdf as multipart file part>"
}
```

Success response example:
```json
{
	"status": "accepted",
	"cv_id": "c1",
	"job_id": "job-parse-001"
}
```

#### GET /cv/current

- Purpose: Retrieve metadata and access information for the user's currently active CV.
- Auth: Protected endpoint (Bearer JWT required).
- Request:
	- Headers: `Authorization: Bearer <token>`
- Success responses: `200 OK`
- Error responses: `401 Unauthorized`, `404 Not Found`, `500 Internal Server Error`

Success response example:
```json
{
	"cv_id": "c1",
	"original_filename": "jane_doe_cv.pdf",
	"content_type": "application/pdf",
	"uploaded_at": "2026-06-05T12:00:00Z",
	"parse_status": "completed",
	"download_url": "https://<host>/api/v1/cv/current/download"
}
```

### Profile

#### GET /profile

- Purpose: Retrieve the current user's profile.
- Auth: Protected endpoint (Bearer JWT required).
- Request:
	- Headers: `Authorization: Bearer <token>`
- Success responses: `200 OK`
- Error responses: `401 Unauthorized`, `404 Not Found`, `500 Internal Server Error`

Success response example:
```json
{
	"user_id": "u1",
	"email": "user@example.com",
	"full_name": "Jane Doe",
	"headline": "Backend Developer",
	"location_components": {
		"country_code": "AR",
		"country_name": "Argentina",
		"region": "Buenos Aires",
		"city": "Buenos Aires",
		"postal_code": "C1000"
	},
	"years_experience": 5,
	"summary": "Backend engineer focused on scalable APIs, cloud infrastructure, and data-intensive services.",
	"skills": ["python", "aws", "sql"],
	"preferred_roles": ["Backend Engineer", "Platform Engineer"],
	"remote_preference": "remote-first",
	"work_mode_preference": "hybrid",
	"experience": [
		{
			"position": "Senior Backend Engineer",
			"company": "TechNova",
			"start_date": "2023-03-01",
			"end_date": null,
			"is_current": true,
			"responsibilities": [
				"Designed and maintained REST APIs for candidate-job matching.",
				"Improved query performance in PostgreSQL for dashboard endpoints."
			]
		},
		{
			"position": "Backend Engineer",
			"company": "DataBridge",
			"start_date": "2020-01-01",
			"end_date": "2023-02-28",
			"is_current": false,
			"responsibilities": [
				"Implemented microservices for profile and notification workflows.",
				"Built integrations with S3, SQS, and observability tooling."
			]
		}
	],
	"education": [
		{
			"degree": "BSc in Computer Science",
			"institution": "University of Buenos Aires",
			"start_date": "2015-03-01",
			"end_date": "2019-12-15",
			"status": "completed"
		}
	],
	"certifications": [
		{
			"name": "AWS Certified Developer - Associate",
			"issuer": "Amazon Web Services",
			"issued_at": "2024-06-10"
		}
	],
	"cv": {
		"cv_id": "c1",
		"parse_status": "completed",
		"last_uploaded_at": "2026-06-05T12:00:00Z"
	},
	"profile_completion_percent": 82
}
```

### Matches

#### GET /matches

- Purpose: Retrieve ranked matches for the current user.
- Auth: Protected endpoint (Bearer JWT required).
- Request:
	- Headers: `Authorization: Bearer <token>`
	- Query params: `limit` (optional), `offset` (optional)
	- URL example: `https://<host>/api/<version>/matches?limit=20&offset=0`
- Success responses: `200 OK`
- Error responses: `400 Bad Request`, `401 Unauthorized`, `500 Internal Server Error`

Notes:
- This endpoint is the user-facing contract for matched offer cards.
- Response items include only card-level offer fields and the source redirect link (`apply_url`).
- Full internal job-offer records are not exposed to end users through a separate jobs-detail endpoint.

Query params example:
```json
{
	"limit": "20",
	"offset": "0"
}
```

Success response example:
```json
{
	"items": [
		{
			"match_id": "m123",
			"job_title": "Senior Backend Engineer",
			"company": "Example Corp",
			"location": "Buenos Aires, AR",
			"work_mode": "hybrid",
			"employment_type": "full-time",
			"seniority": "senior",
			"salary_range": {
				"currency": "USD",
				"min": 45000,
				"max": 65000,
				"period": "year"
			},
			"posted_at": "2026-05-28T10:30:00Z",
			"short_description": "Build and scale backend APIs for a matching platform.",
			"job_platform": "linkedin",
			"apply_url": "https://jobs.example.com/backend-senior-123"
		},
		{
			"match_id": "m124",
			"job_title": "Platform Engineer",
			"company": "CloudBridge",
			"location": "Remote (LATAM)",
			"work_mode": "remote",
			"employment_type": "full-time",
			"seniority": "mid-senior",
			"salary_range": {
				"currency": "USD",
				"min": 50000,
				"max": 72000,
				"period": "year"
			},
			"posted_at": "2026-06-01T08:15:00Z",
			"short_description": "Own platform tooling, CI/CD pipelines, and cloud reliability.",
			"job_platform": "company_site",
			"apply_url": "https://careers.cloudbridge.io/jobs/platform-engineer-987"
		}
	],
	"pagination": {
		"limit": 20,
		"offset": 0,
		"total": 124
	}
}
```

#### POST /matches/{id}/optimize-cv

- Purpose: Request asynchronous CV optimization for a specific match.
- Auth: Protected endpoint (Bearer JWT required).
- Request:
	- Headers: `Authorization: Bearer <token>`
	- Path param: `id` (required, match identifier)
	- Body: none
- Success responses: `202 Accepted`
- Error responses: `400 Bad Request`, `401 Unauthorized`, `404 Not Found`, `500 Internal Server Error`
- Async message published: [optimize_cv_requested](services/api-service.md)


Success response example:
```json
{
	"status": "accepted",
	"optimization_request_id": "opt-456",
	"match_id": "m123",
	"cv_id": "c1",
	"status_url": "/api/v1/optimizations/opt-456/status"
}
```

#### GET /optimizations/{optimization_request_id}/status

- Purpose: Retrieve the current status and result metadata of a CV optimization request.
- Auth: Protected endpoint (Bearer JWT required).
- Request:
	- Headers: `Authorization: Bearer <token>`
	- Path param: `optimization_request_id` (required)
- Success responses: `200 OK`
- Error responses: `401 Unauthorized`, `404 Not Found`, `500 Internal Server Error`



Success response example:
```json
{
	"optimization_request_id": "opt-456",
	"match_id": "m123",
	"cv_id": "c1",
	"status": "completed",
	"updated_at": "2026-06-05T12:05:20Z",
	"optimized_cv": {
		"cv_id": "c1-opt-456",
		"download_url": "https://<host>/api/<version>/optimizations/opt-456/download?sig=<signed_token>",
		"url_expires_at": "2026-06-05T12:10:20Z"
	}
}
```

Notes:
- `download_url` must be a short-lived signed URL scoped to the authenticated user/session.
- Expired or reused URLs should be rejected.

Status values:
- `pending`
- `processing`
- `completed`
- `failed`

#### GET /matches/{id}/optimized-cv

- Purpose: Retrieve the latest optimized CV for a specific match using only the match ID.
- Auth: Protected endpoint (Bearer JWT required).
- Request:
	- Headers: `Authorization: Bearer <token>`
	- Path param: `id` (required, match identifier)
- Success responses: `200 OK`, `202 Accepted` (optimization still in progress)
- Error responses: `401 Unauthorized`, `404 Not Found`, `500 Internal Server Error`

Success response example (`200 OK`):
```json
{
	"match_id": "m123",
	"status": "completed",
	"optimized_cv": {
		"cv_id": "c1-opt-456",
		"download_url": "https://<host>/api/v1/matches/m123/optimized-cv/download?sig=<signed_token>",
		"url_expires_at": "2026-06-05T12:10:20Z",
		"generated_at": "2026-06-05T12:05:20Z"
	}
}
```

In-progress response example (`202 Accepted`):
```json
{
	"match_id": "m123",
	"status": "processing"
}
```

### Notifications Preferences

#### GET /notifications/preferences

- Purpose: Retrieve notification preferences for the current user.
- Auth: Protected endpoint (Bearer JWT required).
- Request:
	- Headers: `Authorization: Bearer <token>`
- Success responses: `200 OK`
- Error responses: `401 Unauthorized`, `404 Not Found`, `500 Internal Server Error`

Success response example:
```json
{
	"email_enabled": true,
	"whatsapp_enabled": true,
	"telegram_enabled": false,
	"sms_enabled": false,
	"push_enabled": false,
	"frequency": "daily"
}
```

#### PUT /notifications/preferences

- Purpose: Update notification preferences for the current user.
- Auth: Protected endpoint (Bearer JWT required).
- Request:
	- Headers: `Authorization: Bearer <token>`, `Content-Type: application/json`
	- Body: preference fields (for example, channel toggles and frequency)
- Success responses: `200 OK`
- Error responses: `400 Bad Request`, `401 Unauthorized`, `500 Internal Server Error`

Request example:
```json
{
	"email_enabled": true,
	"whatsapp_enabled": true,
	"telegram_enabled": false,
	"sms_enabled": false,
	"push_enabled": false,
	"frequency": "daily"
}
```

Success response example:
```json
{
	"status": "updated",
	"preferences": {
        "email_enabled": true,
        "whatsapp_enabled": true,
        "telegram_enabled": false,
        "sms_enabled": false,
        "push_enabled": false,
        "frequency": "daily"
    }
}
```

## Request and Response Conventions

- Request bodies and responses use JSON unless explicitly documented otherwise.
- Protected endpoints require `Authorization: Bearer <token>`.
- Long-running operations return `202 Accepted` and are processed asynchronously.
- Request examples show only request content (body/query), not headers.

## Error Model

Standard error response shape:

```json
{
	"error": {
		"code": "INVALID_INPUT",
		"message": "email must be a valid email address",
		"details": {
			"field": "email"
		}
	},
	"retryable": false,
	"request_id": "req-123"
}
```

Error field rules:
- `error.code`: Stable machine-readable code used by clients.
- `error.message`: User-safe message (no internal stack traces).
- `error.details`: Optional structured validation/debug context.
- `retryable`: Indicates whether the client may retry safely.
- `request_id`: Correlation identifier for logs and support.

HTTP status and code mapping:

| HTTP status | error.code (examples) | When to use | retryable |
|-------------|------------------------|-------------|-----------|
| 400 Bad Request | `INVALID_INPUT`, `INVALID_QUERY_PARAMS` | Request schema/params are invalid | false |
| 401 Unauthorized | `UNAUTHORIZED`, `TOKEN_EXPIRED`, `TOKEN_INVALID` | Missing or invalid auth token | false |
| 404 Not Found | `RESOURCE_NOT_FOUND` | Resource does not exist or is not visible to caller | false |
| 409 Conflict | `EMAIL_ALREADY_EXISTS` | Resource state conflict (for example register existing email) | false |
| 413 Payload Too Large | `FILE_TOO_LARGE` | Uploaded file exceeds size limit | false |
| 422 Unprocessable Content | `UNSUPPORTED_FILE_FORMAT`, `FILE_CORRUPTED` | File is syntactically valid request but not processable pre-queue | false |
| 429 Too Many Requests | `RATE_LIMIT_EXCEEDED` | Rate limit exceeded | true |
| 500 Internal Server Error | `INTERNAL_ERROR` | Unexpected server-side failure | true |

Async behavior notes:
- Endpoints that start async work return `202 Accepted` when the job is queued.
- Failures discovered later in background processing are returned by status endpoints (for example optimization status), not by the original trigger endpoint.
- For downloadable optimized CVs, `download_url` should be short-lived and signed; expired URLs should return `401` or `404`.
