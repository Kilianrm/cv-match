# Sequence Diagram: Manual Profile Edit Flow

## Purpose

Describe the end-to-end flow where the user manually updates profile information from the frontend.

## Flow 05: User Edits Profile Manually

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as Frontend Web App
    participant API as API Gateway
    participant PROFILE as Profile Service
    participant RDS as Shared PostgreSQL

    U->>FE: Edit profile fields and click Save
    FE->>API: PUT /api/v1/profile <access_token, profile_payload>
    API->>PROFILE: PUT /internal/users/{user_id}/profile (profile_payload)
    PROFILE->>PROFILE: Validate editable profile fields

    alt Profile Payload Valid
        PROFILE->>RDS: Update profile sections and updated_at
        RDS-->>PROFILE: Update successful
        PROFILE-->>API: 200 OK {profile_completion_percent}
        API-->>FE: 200 OK {status:"updated", profile_completion_percent}
        FE-->>U: Show "Profile updated"
    else Profile Payload Invalid
        PROFILE-->>API: 400 Bad Request {validation_errors}
        API-->>FE: 400 Bad Request {validation_errors}
        FE-->>U: Show field-level validation errors
    end
```

## Notes

- This is a user-initiated synchronous update flow.
- Authentication is required, but JWT validation steps are omitted for diagram clarity.
- Only editable profile fields are accepted in this endpoint.
- In this MVP version, manual profile updates do not trigger matching automatically.
