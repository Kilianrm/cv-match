# Roadmap: Profile Service

## Purpose

Deliver the first working user journey locally, without any cloud dependency. Scope is intentionally small: login, CV upload (no parsing), profile view, and full profile edit.

## Approach

- No real cloud services. All AWS services are simulated locally via LocalStack.
- S3 (CV file storage) and SQS (async queues) run through LocalStack.
- All services run via Docker Compose on localhost.
- Move to real AWS after this roadmap is validated end-to-end.

## User Journeys In Scope

1. **Login** - user authenticates via Cognito-backed gateway flow.
2. **CV Upload** - user uploads a PDF or DOCX file; file is saved locally; no parsing happens.
3. **CV Delete** - user can delete the active CV and clear its metadata from the profile.
4. **Profile View** - authenticated user sees their full profile.
5. **Profile Edit** - user can edit all profile sections: basic info, location, skills, preferred roles, experience, education, certifications.

## Infrastructure

- Docker Compose: `profile-service`, `postgres`, `gateway-service`, `localstack`.
- LocalStack simulates S3 (CV storage) and SQS (async queues).
- Internal service calls over the Docker network.

## Tables Required

- `users`
- `profiles`
- `cv_upload_records`
- `countries`
- `regions`
- `cities`
- `skills`
- `profile_skills`
- `profile_preferred_roles`
- `profile_experience`
- `profile_education`
- `profile_certifications`

## Endpoints

**Gateway (Public):**
- `POST /api/v1/auth/session` - start application session from Cognito JWT.
- `GET /api/v1/profile` - get full authenticated user profile.
- `PUT /api/v1/profile` - update base profile fields.
- `POST /api/v1/profile/cv` - upload CV file (store locally, no parsing).
- `GET /api/v1/profile/cv` - get active CV metadata for the authenticated user.
- `DELETE /api/v1/profile/cv` - delete active CV metadata and stored file.
- `POST /api/v1/profile/skills` - add one skill.
- `DELETE /api/v1/profile/skills/{skill_id}` - remove one skill.
- `POST /api/v1/profile/preferred-roles` - add one preferred role.
- `PUT /api/v1/profile/preferred-roles/{id}` - update one preferred role.
- `DELETE /api/v1/profile/preferred-roles/{id}` - remove one preferred role.
- `POST /api/v1/profile/experience` - add one experience item.
- `PUT /api/v1/profile/experience/{id}` - update one experience item.
- `DELETE /api/v1/profile/experience/{id}` - remove one experience item.
- `POST /api/v1/profile/education` - add one education item.
- `PUT /api/v1/profile/education/{id}` - update one education item.
- `DELETE /api/v1/profile/education/{id}` - remove one education item.
- `POST /api/v1/profile/certifications` - add one certification.
- `PUT /api/v1/profile/certifications/{id}` - update one certification.
- `DELETE /api/v1/profile/certifications/{id}` - remove one certification.
- `GET /api/v1/locations/countries` - list countries.
- `GET /api/v1/locations/regions?country_code=...` - list regions for a country.
- `GET /api/v1/locations/cities?country_code=...&region_id=...` - list cities.
- `GET /api/v1/catalogs/skills` - list skill catalog.
- `GET /api/v1/catalogs/roles` - list role catalog.
- `GET /api/v1/catalogs/degree-types` - list degree type catalog.

**Frontend Authentication Endpoints (Next.js):**
- `GET /api/auth/login` - start Cognito Hosted UI login flow.
- `GET /api/auth/callback` - exchange authorization code for tokens and create session cookies.
- `GET /api/auth/logout` - clear session cookies and redirect to Cognito logout.
- Note: these routes are implemented in the frontend app and are not gateway `/api/v1` endpoints.

**Profile Service (Internal):**
- `POST /internal/users/sync-from-jwt`
- `GET /internal/users/{user_id}/profile`
- `PUT /internal/users/{user_id}/profile`
- `POST /internal/users/{user_id}/cv`
- `GET /internal/users/{user_id}/cv`
- `DELETE /internal/users/{user_id}/cv`
- `POST /internal/users/{user_id}/skills`
- `DELETE /internal/users/{user_id}/skills/{skill_id}`
- `POST /internal/users/{user_id}/preferred-roles`
- `PUT /internal/users/{user_id}/preferred-roles/{id}`
- `DELETE /internal/users/{user_id}/preferred-roles/{id}`
- `POST /internal/users/{user_id}/experience`
- `PUT /internal/users/{user_id}/experience/{id}`
- `DELETE /internal/users/{user_id}/experience/{id}`
- `POST /internal/users/{user_id}/education`
- `PUT /internal/users/{user_id}/education/{id}`
- `DELETE /internal/users/{user_id}/education/{id}`
- `POST /internal/users/{user_id}/certifications`
- `PUT /internal/users/{user_id}/certifications/{id}`
- `DELETE /internal/users/{user_id}/certifications/{id}`
- `GET /internal/locations/countries`
- `GET /internal/locations/regions?country_code=...`
- `GET /internal/locations/cities?country_code=...&region_id=...`
- `GET /internal/catalogs/skills`
- `GET /internal/catalogs/roles`
- `GET /internal/catalogs/degree-types`
- `GET /health`

## Implementation Order

1. **Service setup** - health endpoint, DB connectivity, gateway routing.
2. **User sync** - `POST /internal/users/sync-from-jwt`, upsert user from JWT.
3. **Location catalog** - seed `countries`, `regions`, `cities`; expose location lookup endpoints.
4. **Profile read** - `GET /api/v1/profile` returning full aggregated profile payload.
5. **Profile base edit** - `PUT /api/v1/profile` for basic info and location.
6. **Profile sub-sections** - skills, preferred roles, experience, education, certifications CRUD.
7. **CV lifecycle** - upload (`POST /api/v1/profile/cv`) and delete (`DELETE /api/v1/profile/cv`) with S3 metadata sync.
8. **Catalog endpoints** - locations plus skills/roles/degree-types to power frontend selectors.
9. **Frontend** - login flow, profile page (view + edit sections + CV upload/delete card).
10. **Tests & CI** - unit + integration tests per slice; CI pipeline on push.

## Tests

**Profile Service:**
- Unit: field validation, data mapping.
- Integration: each endpoint against PostgreSQL.

**Gateway:**
- Integration: auth flow, token handling, routing.

**Frontend:**
- Manual verification plus lint/build checks in this phase.
- Checklist:
  - [X] Login flow completes and session is stored.
  - [X] Profile page loads with full data.
  - [X] Each profile section can be edited and saved.
  - [X] CV upload succeeds and status updates in the UI.
  - [X] CV delete removes the active file and refreshes UI state.

**CI:**
- Unit + integration tests only on every push. No frontend tests in CI for this phase.

## Done Criteria

- All services start with `docker compose up`.
- Login, profile view, profile edit, and CV upload work end-to-end locally.
- CV delete works end-to-end and removes active file metadata.
- All profile sections are editable and changes persist in PostgreSQL.
- CV file is stored in LocalStack S3 and metadata recorded in `cv_upload_records`.
- No real cloud service is required to run the full flow.
- All tests pass locally and in CI.

