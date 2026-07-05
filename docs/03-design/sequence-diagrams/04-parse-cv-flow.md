# Sequence Diagram: Parse CV Requested and Review Flow

## Purpose

Describe the asynchronous flow where CV Parser Service consumes a parse request, stores reviewable suggestions through Profile Service, and the user explicitly applies accepted changes.

## Flow 04: CV Parser Consumes parse_cv_requested with User Review

```mermaid
sequenceDiagram
    autonumber
    participant QP as CV Parser Owned Queue
    participant PARSER as CV Parser Service
    participant S3 as CV File Storage (S3)
    participant PROFILE as Profile Service
    participant API as API Gateway
    participant FE as Frontend Web App
    participant RDS as Shared PostgreSQL

    QP-->>PARSER: parse_cv_requested {user_id, cv_id, trace_id}
    PARSER->>PARSER: Derive s3_key = cv/{user_id}/{cv_id}.pdf
    PARSER->>S3: get_cv
    S3-->>PARSER: file_bytes
    PARSER->>PARSER: Extract and normalize profile fields

    alt Parse Succeeds
        PARSER->>PROFILE: POST /internal/users/{user_id}/parse-suggestions
        PROFILE->>RDS: Persist suggestion batch and items as pending
        PROFILE->>RDS: Mark CV as parsed for user
        PROFILE-->>PARSER: 200 OK
        FE->>API: GET /api/v1/profile/parse-suggestions
        API->>PROFILE: GET internal parse suggestions
        PROFILE-->>API: pending suggestions
        API-->>FE: pending suggestions
        FE->>API: POST /api/v1/profile/parse-suggestions/apply (accepted decisions)
        API->>PROFILE: apply accepted suggestions
        PROFILE->>RDS: Upsert canonical profile sections only for accepted suggestions
        PROFILE-->>API: 200 OK
        API-->>FE: applied summary
    else Parse Fails
        Note over PARSER: Mark parse as failed and route message to retry/DLQ policy
    end
```
