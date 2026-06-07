# Sequence Diagram: Parse CV Requested Flow

## Purpose

Describe the asynchronous flow where CV Parser Service consumes a parse request, reads the CV file, extracts structured profile data, and publishes the result.

## Flow 04: CV Parser Consumes parse_cv_requested

```mermaid
sequenceDiagram
    autonumber
    participant QP as CV Parser Owned Queue
    participant PARSER as CV Parser Service
    participant S3 as CV File Storage (S3)
    participant PROFILE as Profile Service
    participant RDS as Shared PostgreSQL

    QP-->>PARSER: parse_cv_requested {user_id, cv_id, trace_id}
    PARSER->>PARSER: Derive s3_key = cv/{user_id}/{cv_id}.pdf
    PARSER->>S3: get_cv
    S3-->>PARSER: file_bytes
    PARSER->>PARSER: Extract and normalize profile fields

    alt Parse Succeeds
        PARSER->>PROFILE: POST /internal/user/{user_id}/profile (profile_updates)
        PROFILE->>RDS: Upsert user profile sections (skills, experience, education)
        PROFILE->>RDS: Mark CV as parsed for user
        PROFILE-->>PARSER: 200 OK
    else Parse Fails
        Note over PARSER: Mark parse as failed and route message to retry/DLQ policy
    end
```
