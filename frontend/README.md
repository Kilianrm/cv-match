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

## Environment

In both cases the **frontend runs locally**. The env file controls which backend it talks to:

| File | Frontend | Backend | Created by |
|---|---|---|---|
| `.env.local` | localhost:3000 | Local gateway + services (localhost) | You, manually ? **this section** |
| `.env.dev` | localhost:3000 | Dev backend hosted in AWS | Deploy script (automatic) |

> **`.env.dev` is not needed locally.** It is generated automatically by `./scripts/support/sync-frontend-env-dev.sh` when deploying the dev environment.

## Local environment setup

### 1. Create Cognito User Pool (AWS Console)

1. Open AWS Cognito > User Pools > Create pool.
2. Set password policy and sign-up settings as needed.
3. Under App Integration:
   - Create App Client (public, PKCE enabled).
   - Set callback URL: `http://localhost:3000/api/auth/callback`
   - Set logout URL: `http://localhost:3000`
   - Enable "Authorization Code Grant" flow.
   - Scopes: openid, email, profile.

### 2. Configure .env.local file:

1. Copy the example file:
   ```bash
   cp .env.example .env.local
   ```
2. Open `.env.local` and replace the placeholders with your Cognito pool values:
   - `<your-domain>` ? your Cognito domain prefix
   - `<region>` ? e.g. `us-east-1`
   - `<your-cognito-app-client-id>` ? App Client ID from Cognito


## Run locally

```bash
npm install
npm run dev:local   # loads .env.local
```

## Run locally pointing to aws dev backend

```bash
npm install
npm run dev:dev   # enforces .env.dev (temporarily ignores .env.local)
```

Open http://localhost:3000.

## Commands

| Command | Env file loaded | Description |
|---|---|---|
| `npm run dev` | `.env.local` (Next.js default) | Standard local dev |
| `npm run dev:local` | `.env.local` (explicit) | Local dev with explicit env |
| `npm run dev:dev` | `.env.dev` only (temporarily disables `.env.local`) | Dev/cloud env |
| `npm run build` | `.env.local` | Production build (local) |
| `npm run build:dev` | `.env.dev` | Production build for dev environment |
| `npm run start` | Build output env at runtime | Start production server after build |
| `npm run lint` | n/a | Run ESLint |

## Architecture notes

- Frontend calls API Gateway endpoints only.
- Internal service endpoints are not browser-facing.
- Access and ID tokens are not stored in localStorage.
- Uses standard OAuth 2.0 Authorization Code + PKCE flow.
- Token validation and user mapping happen in the API Gateway.

Detailed strategy is documented in docs/04-implementation/frontend-strategy.md.
