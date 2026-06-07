# Sequence Diagram: Create User Flow

## Purpose

Describe the first end-to-end flow of the system using direct frontend authentication with Cognito, followed by backend user synchronization.

## Flow 01: Register User

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as Frontend Web App
    participant AUTH as Cognito
    participant API as API Gateway
    participant PROFILE as Profile Service
    participant DB as PostgreSQL (Users)

    U->>FE: Submit registration form (email, password)
    FE->>AUTH: SignUp(email, password)

    alt Cognito signup success
        AUTH-->>FE: Signup accepted (confirmation required)
        U->>FE: Confirm account code
        FE->>AUTH: ConfirmSignUp(code)
        AUTH-->>FE: Account confirmed
        FE->>AUTH: SignIn(email, password)
        AUTH-->>FE: {access_token, id_token, refresh_token}

        FE->>API: POST /api/v1/auth/session <Bearer access_token>
        API->>AUTH: Validate JWT (JWKS/claims)
        AUTH-->>API: Token valid
        API->>PROFILE: POST /internal/users/sync-from-jwt
        PROFILE->>DB: upsert_user
        DB-->>PROFILE: {OK}
        PROFILE-->>API: {OK}
        API-->>FE: 200 OK {status:"authenticated", is_new_user:true}
        FE-->>U: Show success + next steps
    else Cognito signup error
        AUTH-->>FE: Error (validation/conflict/rate limit)
        FE-->>U: Show error message
    end
```