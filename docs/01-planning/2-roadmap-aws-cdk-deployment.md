# Roadmap: AWS CDK Deployment Foundation

## Purpose

Deploy the current validated local MVP to AWS with a safe, non-production-first approach, preserving current behavior while improving operability.

## Approach

- Use AWS CDK as the single infrastructure definition.
- Start with one `dev` environment and a predictable release flow.
- Keep service contracts unchanged while moving runtime from Docker Compose to AWS.
- Prioritize CloudWatch log visibility and rollback safety.

## User Journeys In Scope

1. **Public API Access** - Users can reach `gateway-service` `/api/v1` routes in AWS `dev` with the same behavior as local MVP.
2. **Profile Lifecycle in AWS** - Users can view and edit profile data end-to-end with Aurora PostgreSQL backing.
3. **CV Lifecycle in AWS** - Users can upload/delete CV files with S3-backed storage and metadata consistency.
4. **Operational Reliability** - Team can deploy, inspect CloudWatch logs, and rollback safely in AWS `dev`.

## Infrastructure

- AWS CDK app with explicit stack boundaries for `dev`: `network`, `security`, `compute`, `data`, `auth`, `profile`, `gateway`.
- Stack names in AWS follow: `cv-match-dev-network`, `cv-match-dev-security`, `cv-match-dev-compute`, `cv-match-dev-data`, `cv-match-dev-auth`, `cv-match-dev-profile`, `cv-match-dev-gateway`.
- One VPC with private subnets for services/database and controlled public entrypoint.
- Dev baseline uses no NAT Gateway by default to reduce cost; outbound egress is enabled only when required by runtime workloads.
- Compute target for `gateway-service` and `profile-service` (CDK-managed runtime).
- RDS PostgreSQL for transactional data.
- S3 for CV storage.
- CloudWatch Logs.
- Secrets Manager (or SSM Parameter Store) for configuration and secrets.


## Implementation Order

1. **CDK foundation** - Bootstrap account/region, stack boundaries, and environment conventions.
2. **Network baseline** - Provision VPC, subnets, route model, and dev egress strategy (NAT disabled by default).
3. **Security baseline** - Provision shared service and database security groups; define ingress and egress rules.
4. **Shared compute (`compute`)** - Provision one shared ECS cluster used by `profile` and `gateway` services.
5. **Data and storage (`data`)** - Provision RDS and S3; validate connectivity.
6. **Authentication (`auth`)** - Provision Cognito user pool, app client, hosted domain, issuer, and JWKS outputs.
7. **Schema bootstrap** - Initialize database schema and seed catalogs in AWS `dev` (first deploy; no migration history required).
8. **Service deployment (`profile` then `gateway`)** - Deploy `profile` first, resolve `ProfileServiceUrl`, then deploy `gateway` with profile base URL wiring; validate route contracts.
9. **Frontend integration mode** - Add explicit support for cloud environment integration in AWS `dev` while keeping frontend deployed locally, with automatic connection to backend APIs and auth/session flow.
10. **Operational visibility** - Ensure CloudWatch log groups and a simple failure investigation workflow for AWS `dev`.

## Tests

**Smoke tests in real AWS (`dev`)**

- Scope: lightweight post-deploy checks against deployed AWS resources (no heavy end-to-end flows).
- Command: `make dev-test SUITE=smoke STACK=<stack|stack1,stack2|full>`
- Runner: `tests/integration/smoke-aws-deployed.test.sh`

Stack-level smoke coverage:
- `network`: stack health and VPC output/resource existence.
- `security`: stack health and required shared security groups existence.
- `compute`: shared ECS cluster output and cluster existence.
- `auth`: Cognito outputs and JWKS endpoint reachability.
- `data`: database endpoint/secret outputs and S3 CV bucket existence.
- `profile`: profile service outputs and CloudWatch log group presence.
- `gateway`: gateway health endpoint (`/health`), public catalog reachability, and CloudWatch log group presence.

Database bootstrap validation (separate, lightweight):
- Bootstrap command: `make dev-bootstrap-db`
- Bootstrap data test command: `make dev-test-bootstrap-db`
- Runner: `tests/integration/bootstrap-dev-db.test.sh`
- Validates minimum seed cardinalities and required reference rows in deployed RDS.

**Frontend (if applicable):**
- Manual verification and basic quality checks for API compatibility after deployment.
- Checklist:
  - [x] Public `/api/v1` routes reachable in AWS `dev`
  - [x] Profile lifecycle works end-to-end in AWS `dev`
  - [x] CV lifecycle works end-to-end in AWS `dev`

## Done Criteria

- [x] CDK stacks (`network`, `security`, `compute`, `data`, `auth`, `profile`, `gateway`) deploy successfully to AWS `dev`.
- [x] In-scope journeys work end-to-end in AWS `dev`.
- [x] Data persistence is validated in RDS and S3.
- [x] Deployed AWS smoke tests pass (`make dev-test SUITE=smoke STACK=full`) and bootstrap DB smoke validation passes (`make dev-test-bootstrap-db`).