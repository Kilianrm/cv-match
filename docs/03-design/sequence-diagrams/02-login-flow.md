# Sequence Diagram: Login Flow

## Purpose

Describe the login flow where the frontend authenticates with Cognito and then starts an application session in API Gateway using JWT.

## Flow 02: Log User

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as Frontend Web App
    participant AUTH as Cognito
    participant API as API Gateway
    participant PROFILE as Profile Service
    participant DB as PostgreSQL (Users)

    U->>FE: Submit login form (email, password)
    FE->>AUTH: SignIn(email, password)

    alt Cognito login success
        AUTH-->>FE: {access_token, id_token, refresh_token}
        FE->>API: POST /api/v1/auth/session <Bearer access_token >
        API->>AUTH: Validate JWT (JWKS/claims)
        AUTH-->>API: Token valid
        API->>PROFILE: POST /internal/users/sync-from-jwt
        PROFILE->>DB: upsert_user
        DB-->>PROFILE: {OK}
        PROFILE-->>API: {OK}
        API-->>FE: 200 OK {status:"authenticated", is_new_user:false}
        FE->>API: GET /api/v1/profile < Bearer access_token >
        API-->>FE: 200 OK {profile_data}
        FE-->>U: Show authenticated state
    else Cognito login error
        AUTH-->>FE: Error (invalid credentials, rate limit, locked account)
        FE-->>U: Show error message
    end
```
