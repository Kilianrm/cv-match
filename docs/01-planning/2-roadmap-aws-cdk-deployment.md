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

- AWS CDK app with stack boundaries: `network`, `security`, `shared-infra`, and service-specific stacks such as `gateway-service`.
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
4. **Data and storage** - Provision RDS and S3; validate connectivity.
5. **Schema bootstrap** - Initialize database schema and seed catalogs in AWS `dev` (first deploy; no migration history required).
6. **Service deployment** - Deploy service-specific stacks starting with `gateway-service`, then add `profile-service` runtime deployment as AWS service wiring is introduced; validate route contracts.
7. **Frontend integration mode** - Add explicit support for cloud environment integration in AWS `dev` while keeping frontend deployed locally, with automatic connection to backend APIs and auth/session flow.
8. **Operational visibility** - Ensure CloudWatch log groups and a simple failure investigation workflow for AWS `dev`.

## Tests

**Component (service-local):**
- Component: `profile-service` component tests validate DB/S3-backed behavior in isolation.
- Unit: service unit tests continue to validate handlers, validation, and store logic quickly.

**Cross-service E2E (smoke):**
- Smoke E2E: auth session, profile read/update, CV upload/delete, and catalog/location endpoints through `gateway-service`.
- Smoke E2E: persistence and contract checks against AWS `dev` data plane (Aurora/RDS + S3).

**Gateway service checks:**
- Gateway-focused checks: routing, auth enforcement, and downstream error mapping in AWS `dev`.

**Frontend (if applicable):**
- Manual verification and basic quality checks for API compatibility after deployment.
- Checklist:
  - [ ] Public `/api/v1` routes reachable in AWS `dev`
  - [ ] Profile lifecycle works end-to-end in AWS `dev`
  - [ ] CV lifecycle works end-to-end in AWS `dev`

## Done Criteria

- [ ] CDK stacks (`network`, `security`, `data`, `gateway`, `profile`) deploy successfully to AWS `dev`.
- [ ] In-scope journeys work end-to-end in AWS `dev`.
- [ ] Data persistence is validated in RDS and S3.
- [ ] Component and cross-service smoke validations pass with health checks.