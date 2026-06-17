# Profile Service

Minimal local-first service exposing internal HTTP endpoints.

## Scope (MVP)

- Internal endpoints:
  - POST /internal/users/sync-from-jwt
  - POST /internal/users/{user_id}/cv
  - POST /internal/users/{user_id}/profile
  - GET /health

## Local stack

- profile-service container (application)
- postgres container (data)
- localstack container (S3 simulation only)

## Quick start

1. Copy .env.example to .env and adjust values.
2. Run: docker compose up --build
3. Health check: GET http://localhost:8080/health
4. Upload CV to simulated S3 for a specific user:

  curl -X POST http://localhost:8080/internal/users/u-1/cv \
     -F "file=@./sample.pdf"

5. Sync user:

   curl -X POST http://localhost:8080/internal/users/sync-from-jwt \
     -H "Content-Type: application/json" \
  -d '{"issuer":"https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxxxx","sub":"9f3c2b1a-7d6e-4a11-9c31-2f8f6b7e1234","email":"user@example.com"}'

6. Upsert profile:

  curl -X POST http://localhost:8080/internal/users/u-1/profile \
     -H "Content-Type: application/json" \
     -d '{"full_name":"Ada Lovelace","headline":"Backend Engineer","location":"Madrid"}'

## How it works

- The upload endpoint stores CV files in S3.
- The object key is deterministic and based only on the user id: cv/{user_id}.
- Before storing, the service performs a lightweight validation:
  - Allowed extensions: .pdf, .doc, .docx, .txt
  - Allowed MIME types for those formats
  - Basic signature checks (for PDF/DOCX)
  - Simple CV keyword heuristic
- In local development, S3 is simulated by LocalStack.
- Queue consumption is intentionally not part of this microservice stage.

