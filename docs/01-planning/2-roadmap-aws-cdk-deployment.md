# Roadmap: AWS CDK Deployment Foundation

## Purpose

Deploy the current validated local MVP to AWS with a safe, non-production-first approach, preserving current behavior while improving operability.

## Approach

- Use AWS CDK as the single infrastructure definition.
- Start with one `dev` environment and a predictable release flow.
- Keep service contracts unchanged while moving runtime from Docker Compose to AWS.
- Prioritize observability, rollback safety, and cost visibility.
- Deliver in small weekly increments over a 4-week execution window.

## User Journeys In Scope

1. **Public API Access** - Users can reach `gateway-service` `/api/v1` routes in AWS `dev` with the same behavior as local MVP.
2. **Profile Lifecycle in AWS** - Users can view and edit profile data end-to-end with Aurora PostgreSQL backing.
3. **CV Lifecycle in AWS** - Users can upload/delete CV files with S3-backed storage and metadata consistency.
4. **Operational Reliability** - Team can deploy, observe, and rollback safely in AWS `dev`.

## Infrastructure

- AWS CDK app with stack boundaries: `network`, `data`, `services`, optional `observability`.
- One VPC with private subnets for services/database and controlled public entrypoint.
- Compute target for `gateway-service` and `profile-service` (CDK-managed runtime).
- Aurora PostgreSQL (or RDS PostgreSQL) for transactional data.
- S3 for CV storage.
- CloudWatch logs, metrics, and alarms.
- Secrets Manager (or SSM Parameter Store) for configuration and secrets.
- CI/CD deploy path to `dev`.


## Implementation Order

1. **CDK foundation** - Bootstrap account/region, stack boundaries, and environment conventions.
2. **Network baseline** - Provision VPC, subnets, route model, security groups, and NAT strategy.
3. **Data and storage** - Provision RDS and S3; validate connectivity.
4. **Schema bootstrap** - Initialize database schema and seed catalogs in AWS `dev` (first deploy; no migration history required).
5. **Service deployment** - Deploy `profile-service` then `gateway-service`; validate route contracts.
6. **Operational settings** - Configure health checks, timeouts, autoscaling thresholds, and diagnostics.
7. **CI/CD rollout** - Add build/test/deploy pipeline with rollback flow.
8. **Observability and cost** - Add dashboards, alarms, budget guardrails, and failure drill.

## Tests

**Service:**
- Integration: smoke checks for auth session, profile read/update, CV upload/delete, and catalog/location endpoints in AWS `dev`.
- Integration: endpoint behavior and persistence against Aurora/RDS.

**Gateway (if applicable):**
- Integration: auth flow, routing, and error handling in AWS `dev`.

**Frontend (if applicable):**
- Manual verification and basic quality checks for API compatibility after deployment.
- Checklist:
  - [ ] Public `/api/v1` routes reachable in AWS `dev`
  - [ ] Profile lifecycle works end-to-end in AWS
  - [ ] CV lifecycle works end-to-end in AWS

**CI:**
- Build/test/deploy workflow from main branch to `dev` with reproducible outcomes.

## Done Criteria

- [ ] CDK stacks (`network`, `data`, `services`) deploy successfully to AWS `dev`.
- [ ] In-scope journeys work end-to-end in AWS `dev`.
- [ ] Data persistence is validated in Aurora/RDS and S3.
- [ ] Integrations are validated with health checks and smoke tests.
- [ ] Service and deployment validations pass locally where applicable.
- [ ] CI pipeline passes for deploy and post-deploy checks.
