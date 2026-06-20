# Roadmap: <Service or Feature Name>

## Purpose

Describe the objective of this roadmap in 2-4 lines.

## Approach

- Define the delivery strategy.
- Clarify key constraints (scope, timeline, dependencies).
- Note local vs cloud assumptions (if relevant).

## User Journeys In Scope

1. **<Journey 1 Name>** - Short description.
2. **<Journey 2 Name>** - Short description.
3. **<Journey 3 Name>** - Short description.
4. **<Journey 4 Name>** - Short description.

## Infrastructure

- Runtime/services involved.
- Local dependencies.
- Network or integration notes.

## Tables Required

- `<table_name_1>`
- `<table_name_2>`
- `<table_name_3>`

## Endpoints

**Gateway (Public):**
- `<METHOD> /api/v1/<resource>` - Description.
- `<METHOD> /api/v1/<resource>` - Description.

**Frontend Authentication Endpoints (if applicable):**
- `<METHOD> /api/auth/<route>` - Description.
- `<METHOD> /api/auth/<route>` - Description.

**Internal Service Endpoints:**
- `<METHOD> /internal/<resource>` - Description.
- `<METHOD> /internal/<resource>` - Description.
- `GET /health`

## Implementation Order

1. **<Phase 1>** - Description.
2. **<Phase 2>** - Description.
3. **<Phase 3>** - Description.
4. **<Phase 4>** - Description.
5. **<Phase 5>** - Description.

## Tests

**Service:**
- Unit: key business logic.
- Integration: endpoint behavior and persistence.

**Gateway (if applicable):**
- Integration: auth, routing, error handling.

**Frontend (if applicable):**
- Manual verification and basic quality checks.
- Checklist:
  - [ ] <Flow 1 validated>
  - [ ] <Flow 2 validated>
  - [ ] <Flow 3 validated>

**CI:**
- Define test scope for each push.

## Done Criteria

- [ ] Services start successfully.
- [ ] In-scope journeys work end-to-end.
- [ ] Data persistence is validated.
- [ ] Integrations are validated.
- [ ] Tests pass locally.
- [ ] Tests pass in CI.
