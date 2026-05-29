# Authentication

## Purpose

Describe authentication and authorization flows for CV Match.

## Identity Provider

CV Match uses Amazon Cognito as the managed identity provider for end-user authentication.

- User directory: Cognito User Pool (email as primary sign-in attribute)
- Protocols: OAuth 2.0 and OpenID Connect (OIDC)
- Client integration: Frontend web app authenticates through a Cognito App Client
- API trust model: API accepts only Cognito-issued JWTs on protected routes
- Domain: Cognito hosted domain for MVP; custom domain (auth.cv-match.com) can be enabled later
- MFA: Optional in MVP, with the ability to enforce it per environment or risk profile

This choice removes the need to build password storage and credential lifecycle logic in-house, while keeping a native integration with AWS services and IAM-based operational controls.

## User Registration Flow

Registration is handled by Amazon Cognito User Pool and follows an email-verification flow.

1. User submits sign-up data (email + password) from the frontend.
2. Frontend calls Cognito sign-up through the App Client.
3. Cognito validates password policy and creates the user in UNCONFIRMED state.
4. Cognito sends a verification code to the user email.
5. User confirms the code; Cognito changes account status to CONFIRMED.
6. After confirmation, CV Match creates or upserts the internal user record in Aurora PostgreSQL using Cognito subject (sub) as the external identity key.
7. The API stores the identity mapping (cognito_sub -> internal user_id) for future token-to-user resolution.

Notes for MVP:
- Use Cognito default email verification to keep implementation simple.
- Keep sign-up errors generic at API/UX level (for example, avoid exposing whether an email is already registered in detail).
- If user provisioning cannot be completed immediately after confirmation, apply lazy provisioning on first authenticated API call.

## Login Flow

Login is handled through Cognito User Pool authentication using the web App Client.

1. User enters credentials (email + password) in the frontend.
2. Frontend sends the authentication request to Cognito.
3. Cognito validates credentials and account status (for example, confirmed user, password policy, optional MFA challenge).
4. If required, Cognito completes additional challenge steps (MFA code, password reset, or new-password challenge).
5. On successful authentication, Cognito returns JWT tokens (ID token, access token, and refresh token).
6. Frontend stores tokens securely according to client strategy and sends the access token in Authorization header for protected API calls.
7. API validates the token, resolves cognito_sub to internal user_id, and authorizes access to user-scoped resources.

Notes for MVP:
- Prefer Authorization Code Flow with PKCE for browser-based clients.
- Keep access tokens short-lived and use refresh token rotation policy supported by Cognito.
- Enforce account lockout and brute-force protection via Cognito defaults and API rate limiting.

## Token Model

CV Match uses Cognito-issued JWTs based on OAuth 2.0/OIDC.

Token types:
- ID token: represents authenticated user identity for client-side user context.
- Access token: used by frontend and approved clients to call protected API endpoints.
- Refresh token: used to obtain new ID/access tokens without forcing a full login.

Core claims expected by the API:
- sub: immutable Cognito user identifier (primary identity key).
- iss: Cognito issuer URL for the user pool.
- aud/client_id: token audience bound to the configured app client.
- exp, iat, nbf: token validity window claims.
- token_use: distinguishes access vs id token.
- scope: optional OAuth scopes for endpoint-level authorization.

Lifetime strategy (MVP baseline):
- Access token: short-lived (for example, 15 to 60 minutes).
- ID token: short-lived and aligned with access token lifetime.
- Refresh token: longer-lived (for example, days to weeks) with revocation support.

Usage rules:
- API authorization accepts only access tokens for resource access.
- ID tokens are not used as bearer credentials for API authorization.
- Refresh tokens are never sent to backend APIs; they are exchanged only with Cognito.
- Token storage must minimize XSS and token leakage risk (prefer secure cookie patterns or equivalent hardened client storage approach).

## Token Validation

All protected API requests must include a bearer access token issued by the configured Cognito User Pool.

Validation steps performed by the API:
1. Extract bearer token from Authorization header.
2. Decode token header and resolve key ID (kid).
3. Retrieve and cache Cognito JWKS for the user pool issuer.
4. Verify JWT signature using the matching public key.
5. Validate issuer (iss) against the expected Cognito user pool URL.
6. Validate audience/client binding (aud or client_id) for the authorized app client.
7. Enforce token_use = access for API authorization.
8. Validate time claims (exp, nbf, iat) with small clock-skew tolerance.
9. Optionally validate required scopes for endpoint-level access control.

Failure handling:
- Missing or malformed token: return 401 Unauthorized.
- Invalid signature, wrong issuer, wrong audience, expired token, or wrong token_use: return 401 Unauthorized.
- Valid token but insufficient scope/permissions: return 403 Forbidden.

Operational guidance:
- Cache JWKS keys with periodic refresh and immediate refresh on unknown kid.
- Do not call Cognito introspection per request; JWT verification is local after key retrieval.
- Emit structured auth failure logs without storing raw tokens.
- Apply API rate limits and WAF rules to reduce token abuse and brute-force traffic.

## User Mapping

CV Match separates external identity (Cognito user) from internal domain identity (application user record).

Mapping model:
- External key: Cognito sub (immutable per user in the User Pool).
- Internal key: user_id (UUID in Aurora PostgreSQL).
- Mapping relation: one Cognito sub -> one internal user_id.

When mapping is created:
- Preferred: immediately after successful email confirmation (post-confirmation provisioning).
- Fallback: lazily on the first authenticated API request when no mapping exists yet.

Resolution flow on each protected request:
1. API validates access token.
2. API extracts sub claim.
3. API looks up mapping by cognito_sub.
4. If mapping exists, request context is enriched with internal user_id.
5. If mapping does not exist, API attempts idempotent create/upsert and then continues.

Data integrity rules:
- Enforce unique constraint on cognito_sub.
- Enforce unique constraint on primary email when required by business rules.
- All create/upsert operations must be idempotent to avoid duplicate users during retries.
- Do not use mutable fields (email, name) as identity keys.

Operational notes:
- Log mapping failures with correlation IDs, never with raw tokens.
- If mapping cannot be established, return 401/403 based on policy and avoid partial domain writes.
- Keep mapping logic centralized in API auth middleware/service to ensure consistency.

## Protected Endpoints

Protected endpoints are API routes that require a valid Cognito access token in the Authorization header before processing.

Endpoint inventory and per-route access requirements are documented in [docs/03-design/api.md](../03-design/api.md).

Authentication/authorization baseline for all protected routes:
- Deny by default unless a route is explicitly public.
- Require full token validation as defined in Token Validation.
- Enforce user ownership with internal user_id resolved from cognito_sub.
- Return 401 for missing/invalid token and 403 for insufficient permissions.

## Authorization Rules

Authorization in CV Match follows a least-privilege, deny-by-default model.

Policy rules (non-duplicated):
- User scope only: each authenticated user can access only their own resources.
- No admin surface in MVP: privileged/admin actions are out of scope and denied by default.
- Separation of concerns: end-user authorization uses Cognito JWT + ownership checks, while service-to-service permissions use IAM roles.

This section defines authorization policy only.
Implementation details are defined in:
- Token checks and error semantics: Token Validation
- Identity resolution: User Mapping
- Route protection baseline and endpoint reference: Protected Endpoints and [docs/03-design/api.md](../03-design/api.md)

## Security Considerations

This section captures authentication-specific controls that complement the broader platform security document.

- Password and account policy: enforce Cognito password policy, verification flow, and lockout protections for repeated failed attempts.
- MFA strategy: keep MFA optional in MVP but enable staged enforcement (for example, admin/internal environments first, then high-risk users).
- Token transport and storage: require HTTPS end-to-end, avoid exposing tokens in URLs, and use hardened client storage patterns to reduce XSS token theft risk.
- Token lifetime and revocation: keep access tokens short-lived, use refresh token revocation/rotation, and force re-authentication after high-risk events (credential reset, suspicious login).
- Abuse resistance: combine API rate limits, WAF protections, and anomaly monitoring to reduce credential stuffing and brute-force attempts.
- Session boundary hygiene: validate issuer/audience/token_use strictly and reject tokens from other pools/clients/environments.
- Logging and privacy: never log raw tokens, auth secrets, or verification codes; log only minimal metadata needed for auditing.
- Secrets handling: keep Cognito app secrets (if used) and related credentials in AWS Secrets Manager with least-privilege access.
- Availability fallback: if Cognito/JWKS retrieval is degraded, fail closed for protected routes and emit operational alerts.

Related references:
- Platform-wide controls: [docs/02-architecture/security.md](security.md)
- Endpoint-level contract and auth requirements: [docs/03-design/api.md](../03-design/api.md)