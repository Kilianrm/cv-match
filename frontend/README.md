# Frontend (CV Match)

Professional and maintainable frontend MVP for CV Match using Next.js App Router.

## What is included

- Branded landing page with login CTA.
- AWS Cognito Hosted UI login flow with PKCE:
	- /api/auth/login
	- /api/auth/callback
	- /api/auth/logout
- Profile screen at /profile that reads data from API Gateway.
- Token-based session via secure HTTP-only cookies.

## Prerequisites

- Node.js 20+
- npm 10+
- AWS Cognito User Pool with an App Client configured for PKCE.

## Environment setup

### 1. Create Cognito User Pool (AWS Console)

1. Open AWS Cognito > User Pools > Create pool.
2. Set password policy and sign-up settings as needed.
3. Under App Integration:
   - Create App Client (public, PKCE enabled).
   - Set callback URL: `http://localhost:3000/api/auth/callback`
   - Set logout URL: `http://localhost:3000`
   - Enable "Authorization Code Grant" flow.
   - Scopes: openid, email, profile.

### 2. Configure frontend env

1. Copy .env.example to .env.local.
2. Replace placeholders with your Cognito values:
   - `AUTH_AUTHORIZATION_ENDPOINT`: Your pool's `/oauth2/authorize` endpoint.
   - `AUTH_TOKEN_ENDPOINT`: Your pool's `/oauth2/token` endpoint.
   - `AUTH_LOGOUT_ENDPOINT`: Your pool's `/logout` endpoint.
   - `AUTH_CLIENT_ID`: Your App Client ID.

Example:

```env
API_GATEWAY_BASE_URL=http://localhost:8080
AUTH_AUTHORIZATION_ENDPOINT=https://your-domain.auth.us-east-1.amazoncognito.com/oauth2/authorize
AUTH_TOKEN_ENDPOINT=https://your-domain.auth.us-east-1.amazoncognito.com/oauth2/token
AUTH_LOGOUT_ENDPOINT=https://your-domain.auth.us-east-1.amazoncognito.com/logout
AUTH_LOGOUT_REDIRECT_PARAM=logout_uri
AUTH_CLIENT_ID=your_cognito_app_client_id
AUTH_REDIRECT_URI=http://localhost:3000/api/auth/callback
AUTH_LOGOUT_REDIRECT_URI=http://localhost:3000
AUTH_SCOPES=openid email profile
```

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Commands

```bash
npm run dev
npm run lint
npm run build
npm run start
```

## Architecture notes

- Frontend calls API Gateway endpoints only.
- Internal service endpoints are not browser-facing.
- Access and ID tokens are not stored in localStorage.
- Uses standard OAuth 2.0 Authorization Code + PKCE flow.
- Token validation and user mapping happen in the API Gateway.

Detailed strategy is documented in docs/04-implementation/frontend-strategy.md.
