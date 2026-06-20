# API Specification

## Purpose

Define the external API contract for CV Match.

## Base Information

### Cognito Authentication

Authentication is handled by Amazon Cognito.

Base URL:
https://<cognito-domain>.auth.<region>.amazoncognito.com

Common endpoints:
- /oauth2/authorize
- /oauth2/token
- /logout

User registration, login, password reset and account management are provided by Cognito Hosted UI or Cognito SDKs, depending on the client implementation.
### API Gateway (Business APIs)

- Use this host for all business endpoints.
- Endpoint pattern: `https://<api-domain>/api/v1/{endpoint}`
- Protected endpoints require `Authorization: Bearer <token>` (token issued by Cognito).
- Current implementation in `gateway-service` includes: auth session, profile, CV management, locations, and catalogs.
- Matches, optimizations, and notifications are documented as planned contracts and may not be active in this phase.


## Endpoint Groups

### 1) Cognito-Exposed Auth Endpoints

```text
https://<cognito-domain>.auth.<region>.amazoncognito.com
|-- register (SignUp)
|-- login (SignIn / InitiateAuth)
`-- logout (GlobalSignOut)
```

### 2) API Gateway Endpoints

```text
/api/v1
|-- /auth
|   `-- POST /auth/session
|-- /profile
|   |-- GET /profile
|   |-- PUT /profile
|   |-- POST /profile/cv
|   |-- GET /profile/cv
|   |-- DELETE /profile/cv
|   |-- POST /profile/skills
|   |-- DELETE /profile/skills/{skill_id}
|   |-- POST /profile/preferred-roles
|   |-- PUT /profile/preferred-roles/{id}
|   |-- DELETE /profile/preferred-roles/{id}
|   |-- POST /profile/experience
|   |-- PUT /profile/experience/{id}
|   |-- DELETE /profile/experience/{id}
|   |-- POST /profile/education
|   |-- PUT /profile/education/{id}
|   |-- DELETE /profile/education/{id}
|   |-- POST /profile/certifications
|   |-- PUT /profile/certifications/{id}
|   `-- DELETE /profile/certifications/{id}
|-- /locations
|   |-- GET /locations/countries
|   |-- GET /locations/regions
|   `-- GET /locations/cities
|-- /catalogs
|   |-- GET /catalogs/skills
|   |-- GET /catalogs/roles
|   `-- GET /catalogs/degree-types
|
|  Planned (not active in this phase):
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

### Auth Session

#### POST /auth/session

- Purpose: Start an application session using a Cognito JWT and ensure the internal user exists.
- Auth: Protected endpoint (Bearer JWT required, token issued by Cognito).
- Request:
	- Headers: `Authorization: Bearer <token>`
	- Body: none
- Behavior:
	- Validate JWT claims.
	- Extract identity fields (`sub`, `email`, `email_verified`).
	- Create the internal user on first login, or update identity attributes if the user already exists.
- Success responses: `200 OK`
- Error responses: `401 Unauthorized`, `500 Internal Server Error`

Success response example:
```json
{
	"status": "authenticated",
	"is_new_user": false
}
```


### CV Management

#### POST /profile/cv

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
	"user_id": "u1",
	"filename": "jane_doe_cv.pdf",
	"content_type": "application/pdf",
	"size_bytes": 123559,
	"bucket": "profile-cv-bucket",
	"object_key": "cv/u1/jane_doe_cv.pdf",
	"cv_upload_record": {
		"id": "8e68c0d0-2d40-4f1f-b48b-909e6dd9f9bb",
		"uploaded_at": "2026-06-20T11:00:00Z",
		"parse_status": "pending",
		"is_active": true,
		"storage_key": "cv/u1/jane_doe_cv.pdf",
		"original_filename": "jane_doe_cv.pdf",
		"content_type": "application/pdf"
	}
}
```

#### GET /profile/cv

- Purpose: Retrieve metadata and access information for the user's currently active CV.
- Auth: Protected endpoint (Bearer JWT required).
- Request:
	- Headers: `Authorization: Bearer <token>`
- Success responses: `200 OK`
- Error responses: `401 Unauthorized`, `500 Internal Server Error`

Success response example:
```json
{
	"status": "success",
	"cv": {
		"id": "8e68c0d0-2d40-4f1f-b48b-909e6dd9f9bb",
		"original_filename": "jane_doe_cv.pdf",
		"storage_key": "cv/u1/jane_doe_cv.pdf",
		"content_type": "application/pdf",
		"parse_status": "pending",
		"uploaded_at": "2026-06-20T11:00:00Z"
	}
}
```

No active CV response example:
```json
{
	"cv": null
}
```

#### DELETE /profile/cv

- Purpose: Delete the user's currently active CV and clear active metadata.
- Auth: Protected endpoint (Bearer JWT required).
- Request:
	- Headers: `Authorization: Bearer <token>`
- Success responses: `204 No Content`
- Error responses: `401 Unauthorized`, `500 Internal Server Error`

Notes:
- If no active CV exists, the endpoint still returns `204 No Content`.

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
	"user": {
		"user_id": "u1",
		"email": "user@example.com"
	},
	"profile": {
		"full_name": "Jane Doe",
		"headline": "Backend Developer",
		"summary": "Backend engineer focused on scalable APIs, cloud infrastructure, and data-intensive services.",
		"country_code": "AR",
		"region_id": "r1",
		"city_id": "c1",
		"years_experience": 5,
		"work_mode_preference": "hybrid"
	},
	"location": {
		"country": {
			"code": "AR",
			"name": "Argentina"
		},
		"region": {
			"id": "r1",
			"name": "Buenos Aires"
		},
		"city": {
			"id": "c1",
			"name": "Buenos Aires"
		}
	},
	"skills": [
		{
			"skill_id": "s1",
			"label": "Python",
			"proficiency_level": null
		},
		{
			"skill_id": "s2",
			"label": "AWS",
			"proficiency_level": null
		}
	],
	"preferred_roles": [
		{
			"id": "pr1",
			"role_name": "Backend Engineer"
		},
		{
			"id": "pr2",
			"role_name": "Platform Engineer"
		}
	],
	"experience": [
		{
			"id": "exp1",
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
			"id": "edu1",
			"degree": "BSc in Computer Science",
			"institution": "University of Buenos Aires",
			"start_date": "2015-03-01",
			"end_date": "2019-12-15",
			"status": "completed"
		}
	],
	"certifications": [
		{
			"id": "cert1",
			"name": "AWS Certified Developer - Associate",
			"issuer": "Amazon Web Services",
			"issued_at": "2024-06-10"
		}
	],
	"cv": {
		"cv_id": "c1",
		"parse_status": "completed",
		"last_uploaded_at": "2026-06-05T12:00:00Z"
	}
}
```

#### PUT /profile

- Purpose: Update the current user's base profile fields only.
- Auth: Protected endpoint (Bearer JWT required).
- Request:
	- Headers: `Authorization: Bearer <token>`, `Content-Type: application/json`
	- Body fields:
		- `full_name`
		- `headline`
		- `summary`
		- `country_code`
		- `region_id`
		- `city_id`
		- `years_experience`
		- `work_mode_preference`
- Success responses: `200 OK`
- Error responses: `400 Bad Request`, `401 Unauthorized`, `404 Not Found`, `422 Unprocessable Content`, `500 Internal Server Error`

Request example:
```json
{
	"full_name": "Jane Doe",
	"headline": "Backend Developer",
	"summary": "Backend engineer focused on scalable APIs.",
	"country_code": "AR",
	"region_id": "r1",
	"city_id": "c1",
	"years_experience": 5,
	"work_mode_preference": "hybrid"
}
```

Success response example:
```json
{
	"status": "updated"
}
```

#### POST /profile/skills

- Purpose: Add a skill to the current user's profile.
- Auth: Protected endpoint (Bearer JWT required).
- Request body: `skill_id` (required), `proficiency_level` (optional)
- Success responses: `201 Created`
- Error responses: `400 Bad Request`, `401 Unauthorized`, `409 Conflict`, `500 Internal Server Error`

#### DELETE /profile/skills/{skill_id}

- Purpose: Remove a skill from the current user's profile.
- Auth: Protected endpoint (Bearer JWT required).
- Success responses: `204 No Content`
- Error responses: `401 Unauthorized`, `404 Not Found`, `500 Internal Server Error`

#### POST /profile/preferred-roles

- Purpose: Add a preferred role entry.
- Auth: Protected endpoint (Bearer JWT required).
- Request body: `role_name` (required)
- Success responses: `201 Created`

#### PUT /profile/preferred-roles/{id}

- Purpose: Update one preferred role entry.
- Auth: Protected endpoint (Bearer JWT required).
- Success responses: `200 OK`

#### DELETE /profile/preferred-roles/{id}

- Purpose: Delete one preferred role entry.
- Auth: Protected endpoint (Bearer JWT required).
- Success responses: `204 No Content`

#### POST /profile/experience

- Purpose: Add one experience item.
- Auth: Protected endpoint (Bearer JWT required).
- Request body fields:
	- `position` (required)
	- `company` (required)
	- `start_date`
	- `end_date`
	- `is_current`
	- `responsibilities`
- Success responses: `201 Created`

#### PUT /profile/experience/{id}

- Purpose: Update one experience item.
- Auth: Protected endpoint (Bearer JWT required).
- Success responses: `200 OK`

#### DELETE /profile/experience/{id}

- Purpose: Delete one experience item.
- Auth: Protected endpoint (Bearer JWT required).
- Success responses: `204 No Content`

#### POST /profile/education

- Purpose: Add one education item.
- Auth: Protected endpoint (Bearer JWT required).
- Request body fields:
	- `degree` (required)
	- `institution` (required)
	- `start_date`
	- `end_date`
	- `status`
- Success responses: `201 Created`

#### PUT /profile/education/{id}

- Purpose: Update one education item.
- Auth: Protected endpoint (Bearer JWT required).
- Success responses: `200 OK`

#### DELETE /profile/education/{id}

- Purpose: Delete one education item.
- Auth: Protected endpoint (Bearer JWT required).
- Success responses: `204 No Content`

#### POST /profile/certifications

- Purpose: Add one certification item.
- Auth: Protected endpoint (Bearer JWT required).
- Request body fields:
	- `name` (required)
	- `issuer` (required)
	- `issued_at`
	- `expires_at`
- Success responses: `201 Created`

#### PUT /profile/certifications/{id}

- Purpose: Update one certification item.
- Auth: Protected endpoint (Bearer JWT required).
- Success responses: `200 OK`

#### DELETE /profile/certifications/{id}

- Purpose: Delete one certification item.
- Auth: Protected endpoint (Bearer JWT required).
- Success responses: `204 No Content`

### Location Catalog

#### GET /locations/countries

- Purpose: Retrieve selectable countries for profile forms.
- Auth: Public endpoint in current gateway phase.
- Success responses: `200 OK`

Success response example:
```json
{
	"items": [
		{ "code": "AR", "name": "Argentina" },
		{ "code": "ES", "name": "Spain" }
	]
}
```

#### GET /locations/regions

- Purpose: Retrieve selectable regions for a country.
- Auth: Public endpoint in current gateway phase.
- Query params: `country_code` (required)
- Success responses: `200 OK`

#### GET /locations/cities

- Purpose: Retrieve selectable cities for a country and optional region.
- Auth: Public endpoint in current gateway phase.
- Query params:
	- `country_code` (required)
	- `region_id` (optional)
- Success responses: `200 OK`

### Catalogs

#### GET /catalogs/skills

- Purpose: Retrieve skill suggestions for profile forms.
- Auth: Public endpoint in current gateway phase.
- Query params: `q` (optional), `category` (optional), `limit` (optional)
- Success responses: `200 OK`

#### GET /catalogs/roles

- Purpose: Retrieve role suggestions for profile forms.
- Auth: Public endpoint in current gateway phase.
- Query params: `q` (optional), `category` (optional), `limit` (optional)
- Success responses: `200 OK`

#### GET /catalogs/degree-types

- Purpose: Retrieve degree type suggestions for education forms.
- Auth: Public endpoint in current gateway phase.
- Query params: `q` (optional), `limit` (optional)
- Success responses: `200 OK`

### Matches

Planned contract. This section may not be implemented in the current local gateway phase.

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

Planned contract. This section may not be implemented in the current local gateway phase.

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
