# Frontend Strategy (MVP)

## Purpose

Define a maintainable, professional frontend approach for CV Match that a backend-focused developer can operate.

## Stack Decision

- Framework: Next.js (App Router) with TypeScript.
- Styling: Tailwind CSS (token-based custom theme).
- Authentication: AWS Cognito Hosted UI using Authorization Code + PKCE.
- Session strategy: secure HTTP-only cookies in frontend server routes.
- Data access: frontend calls API Gateway endpoints only.

This keeps credential handling and OAuth lifecycle delegated to AWS while keeping the frontend operationally simple.

## Implemented in Repository

Directory:
- frontend/

Core pages and routes:
- Landing page with login CTA.
- /(authenticated)/dashboard page.
- /(authenticated)/profile page for profile read and edit.
- /(authenticated)/matches page.
- /(authenticated)/optimization page.
- /(authenticated)/notifications page (feature-flag fallback when backend is not enabled).
- /api/auth/login route to start OAuth PKCE flow.
- /api/auth/callback route to exchange code for tokens.
- /api/auth/logout route to clear session and redirect to Cognito logout.
- /api/v1/[...path] route to proxy authenticated frontend requests to gateway `/api/v1/*`.

Notes:
- Standalone `/cv-upload` page was removed; CV upload/delete is handled inside `/profile`.
- Frontend API calls use `/api/v1/...` syntax and do not use `/api/gateway/...` paths.

## Visual Direction

Theme goals:
- Professional, warm, and modern.
- Clear hierarchy for profile information.
- Subtle gradients and elevated cards.

Color tokens:
- Primary: #0E7C86
- Primary strong: #0B636C
- Accent: #F05D5E
- Background: #F7F5F2
- Foreground: #1F2A37
- Muted: #5B6778

Typography:
- Headings: Sora.
- Body: Source Sans 3.

## Environment Variables

Use frontend/.env.local based on frontend/.env.example.

Required Cognito variables:
- API_GATEWAY_BASE_URL: API Gateway base URL used by the frontend `/api/v1` proxy route
- AUTH_AUTHORIZATION_ENDPOINT: Cognito /oauth2/authorize endpoint
- AUTH_TOKEN_ENDPOINT: Cognito /oauth2/token endpoint
- AUTH_LOGOUT_ENDPOINT: Cognito /logout endpoint
- AUTH_LOGOUT_REDIRECT_PARAM: always "logout_uri" for Cognito
- AUTH_CLIENT_ID: Your Cognito App Client ID
- AUTH_REDIRECT_URI: http://localhost:3000/api/auth/callback (must match Cognito config)
- AUTH_LOGOUT_REDIRECT_URI: http://localhost:3000 (must match Cognito config)
- AUTH_SCOPES: openid email profile

Optional variables:
- NEXT_PUBLIC_API_GATEWAY_BASE_URL: fallback base URL for local/dev setups
- NEXT_PUBLIC_NOTIFICATIONS_API: `true` to enable live notifications API calls in UI

## Local Run

From frontend/:

1. npm install
2. Copy .env.example to .env.local and fill Cognito values
3. npm run dev
4. Open http://localhost:3000
5. Click login to start Cognito Hosted UI flow

## Hybrid Deployment Mode (Recommended for Current Stage)

To control AWS cost and reduce operational complexity while the platform is still growing, the frontend can remain local while backend microservices run in AWS `dev`.

Target model:

- Frontend runtime: local (`npm run dev` in `frontend/`)
- Backend runtime: AWS `dev` (gateway-service and downstream services deployed with CDK)
- Infrastructure as Code scope: backend and shared infrastructure first; frontend cloud hosting can be added later

Required configuration for this mode:

1. Set `API_GATEWAY_BASE_URL` in `frontend/.env.local` to the deployed AWS gateway URL.
2. Ensure Cognito app client includes localhost callback/logout URLs for frontend local auth flow.
3. Ensure gateway/API CORS allows the local frontend origin.
4. Keep environment-specific values separated between local frontend and AWS backend.

Why this mode is acceptable now:

- It keeps end-to-end product iteration fast.
- It avoids adding another always-on cloud runtime while multiple backend services are already active.
- It preserves the current frontend architecture and auth model.

Known trade-offs:

- Cloud-to-cloud browser parity is not full yet (frontend is not hosted in AWS).
- Team/demo sharing is less convenient than a fully deployed frontend.
- A future step is still needed to host frontend in AWS (for example ECS or managed hosting) when cost/priority allows.

## Security Notes

- Keep access/id tokens in HTTP-only cookies, not localStorage.
- Use HTTPS in non-local environments.
- Cognito callback URLs must exactly match frontend deployment domain in all environments.
- Frontend should never call internal microservice endpoints directly.
- API Gateway validates Cognito tokens and maps sub to internal user_id.

## Next Iterations

1. Wire education degree input to `/api/v1/catalogs/degree-types` suggestions/select.
2. Enable notifications API integration by default when backend endpoints are available.
3. Add protected route middleware for authenticated pages.
4. Add frontend smoke/e2e coverage for profile CV upload/delete and section CRUD.

## Profile Form Spec (MVP)

Use one authenticated profile page with section cards instead of one long flat form.

### Page Structure

Order on page:
1. Profile header
2. CV upload card
3. Basic info card
4. Location card
5. Skills card
6. Preferred roles card
7. Experience card
8. Education card
9. Certifications card

Each card should:
- Show its own save state.
- Validate only its own fields.
- Be independently editable without blocking the rest of the page.

### Section Design

**Profile header**
- Show full name, email, and a small completion indicator.
- Email should be read-only if it is sourced from Cognito.

**CV upload card**
- Show current CV status: no CV, uploaded, processing, failed.
- Primary action: upload or replace CV.
- After successful upload, poll parse status and show a "Review parsed suggestions" CTA when suggestions are ready.

**Basic info card**
- Fields:
	- `full_name`: text input, required
	- `headline`: text input, optional
	- `summary`: textarea, optional
- UX:
	- Save button inside the card.
	- Inline validation below each field.

**Location card**
- Fields:
	- `country_code`: searchable select, required
	- `region_id`: searchable select, enabled after country is selected
	- `city_id`: searchable select, enabled after country or region is selected
- UX:
	- Do not use free-text location inputs in the main form.
	- If imported CV data cannot be normalized, show it as a review hint, not as the final saved value.

**Skills card**
- Fields:
	- `skills`: multi-value chip input backed by catalog suggestions
	- optional `proficiency_level` per skill only if needed in MVP
- UX:
	- Typeahead should suggest normalized skills from `skills` table.
	- User can add and remove chips quickly.
	- Prevent duplicate skills.

**Preferred roles card**
- Fields:
	- `preferred_roles`: multi-value chip input with suggestions
- UX:
	- Use normalized suggestions where possible.
	- Keep manual entry only as a fallback if taxonomy is not ready yet.

**Experience card**
- UI pattern:
	- Repeatable list of experience items.
	- Each item opens in a compact editable card or drawer.
- Fields per item:
	- `position`: required
	- `company`: required
	- `start_date`: month/year
	- `end_date`: month/year
	- `is_current`: checkbox
	- `responsibilities`: multiline textarea with one bullet per line
- UX:
	- If `is_current` is checked, disable `end_date`.
	- Support add, edit, delete, and reorder.

**Education card**
- UI pattern:
	- Repeatable list of education items.
- Fields per item:
	- `degree`: required
	- `institution`: required
	- `start_date`: month/year, optional
	- `end_date`: month/year, optional
	- `status`: select (`completed`, `in_progress`, `dropped`)
- UX:
	- Support add, edit, delete, and reorder.

**Certifications card**
- UI pattern:
	- Repeatable list of certification items.
- Fields per item:
	- `name`: required
	- `issuer`: required
	- `issued_at`: month/year, optional
	- `expires_at`: month/year, optional
- UX:
	- Support add, edit, and delete.

### Save Behavior

Use mixed save behavior:
- Basic info and location: explicit save button per card.
- Skills and preferred roles: save on card submit.
- Experience, education, and certifications: save the whole section after add/edit/delete actions.

Do not use one global page submit button for the entire profile.

### Validation Rules

Minimum MVP validation:
- `full_name` is required.
- `country_code` is required.
- `position`, `company` required for experience items.
- `degree`, `institution` required for education items.
- `name`, `issuer` required for certification items.
- End date cannot be earlier than start date.
- Duplicate skills should be rejected.

### CV Prefill Behavior

When CV parsing returns structured data:
- Do not silently overwrite canonical profile values.
- Load suggestions from `/api/v1/profile/parse-suggestions`.
- Show diffs per section: current value vs suggested value.
- Let users accept/decline by section and by item.
- Apply accepted suggestions only after explicit confirmation through `/api/v1/profile/parse-suggestions/apply`.

### Review Imported Data UX

- Show a dedicated review panel after parse completion.
- Provide quick actions: `Accept all`, `Decline all`, `Accept section`, `Decline section`.
- Mark low-confidence suggestions as "Needs review" and avoid pre-selecting them as accepted.
- Show apply summary after confirmation, for example: "6 changes applied, 2 declined".
- Keep declined suggestions hidden from normal edit forms unless user opens review history.

### First-Run Onboarding UX

Recommended first authenticated path:
1. Upload CV (optional)
2. Wait for parse completion
3. Review suggestions (accept/decline/skip)
4. Continue to profile dashboard

Rules:
- Upload can be skipped.
- Suggestion review can be skipped without blocking profile usage.
- If skipped, show a persistent "Suggestions pending" indicator on profile.

### Ongoing CV Management UX

- Keep CV upload and suggestion review in the same profile domain (CV card + review panel).
- CV card remains visible after decisions are applied, with status and last upload metadata.
- Uploading a new CV creates a new suggestion batch and does not delete history immediately.

### Conflict UX Rules

- Separate normal suggestions from conflict suggestions in UI.
- For conflict suggestions, require explicit resolution action before apply:
	- `keep existing`
	- `replace existing`
	- `merge`
	- `add as separate`
- Highlight timeline overlap conflicts in experience with side-by-side comparison.

### Mobile Behavior

- Stack cards vertically.
- Keep one primary action per card.
- Avoid large modal flows for every edit.
- Use inline expandable sections for repeatable lists when possible.

### Recommended Frontend Data Contract Shape

The page should work best if `GET /profile` returns one aggregated payload shaped for the UI, for example:

```ts
type ProfilePageResponse = {
	user: {
		email: string;
	};
	profile: {
		fullName: string | null;
		headline: string | null;
		summary: string | null;
		countryCode: string | null;
		regionId: string | null;
		cityId: string | null;
		yearsExperience: number | null;
		workModePreference: 'remote' | 'hybrid' | 'onsite' | 'flexible' | null;
	};
	cv: {
		status: 'none' | 'uploaded' | 'processing' | 'failed';
		filename: string | null;
		uploadedAt: string | null;
	};
	skills: Array<{
		skillId: string;
		label: string;
		proficiencyLevel: string | null;
	}>;
	preferredRoles: Array<{
		id: string;
		roleName: string;
	}>;
	experience: Array<{
		id: string;
		position: string;
		company: string;
		startDate: string | null;
		endDate: string | null;
		isCurrent: boolean;
		responsibilities: string[];
	}>;
	education: Array<{
		id: string;
		degree: string;
		institution: string;
		startDate: string | null;
		endDate: string | null;
		status: 'completed' | 'in_progress' | 'dropped' | null;
	}>;
	certifications: Array<{
		id: string;
		name: string;
		issuer: string;
		issuedAt: string | null;
		expiresAt: string | null;
	}>;
};
```
