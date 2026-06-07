# Security

## Purpose

Describe the security model, baseline controls, and operational security practices for CV Match.

Security goals for MVP:
- Protect user identity and CV data.
- Enforce least privilege across services.
- Reduce common web and cloud attack risk.
- Keep controls practical for a portfolio-scale project.

## Threat Surface

Main exposed surfaces:
- Public frontend (CloudFront + static assets).
- Public API entry point (ALB -> API service).
- Authentication interfaces (Cognito sign-up/login/token flows).
- Asynchronous event paths (SQS + worker consumers).
- Data stores (Aurora PostgreSQL, S3 CV storage, Secrets Manager).
- External integrations (job-source scraping and SES email delivery).

Primary threat categories:
- Credential attacks: brute force, token theft, session misuse.
- API abuse: broken access control, parameter tampering, injection attempts.
- Data exposure: overly permissive IAM, misconfigured buckets, sensitive logs.
- Queue abuse: poisoned/replayed messages and idempotency failures.
- Supply chain/deployment risk: vulnerable dependencies or misconfigured releases.

MVP risk posture:
- Prioritize high-impact controls first (authn/authz, encryption, IAM, logging).
- Accept limited residual risk where mitigation cost is high and exposure is low.

## Identity and Access Management

End-user identity:
- Amazon Cognito User Pool is the identity provider.
- API accepts only valid Cognito access tokens on protected routes.
- Authorization is deny-by-default with strict user ownership checks.
- Internal mapping uses cognito_sub -> internal user_id with idempotent provisioning.

Service identity:
- One IAM task role per service (API, parser, scraper, matcher, notification).
- Roles are scoped to minimum actions and minimum resources.
- No shared broad admin role across services.
- API role baseline: read/write Aurora, read/write S3, SQS send/receive, Secrets read.
- Worker role baseline: read/write Aurora, read S3, SQS receive, SES send, Secrets read.

Authorization principles:
- Least privilege everywhere.
- Separate end-user authorization (JWT + ownership) from service authorization (IAM).
- Return 401 for invalid/missing auth and 403 for valid auth without permission.

## Data Protection

Data in transit:
- Enforce HTTPS/TLS 1.2+ for client-to-edge and edge-to-service communication.
- Reject plaintext transport to protected endpoints.

Data at rest:
- Aurora PostgreSQL encrypted at rest (KMS-backed).
- S3 buckets encrypted at rest.
- Secrets encrypted and stored in Secrets Manager.
- Cognito stores passwords using managed secure hashing mechanisms.

Sensitive data handling:
- Never log raw CV content, tokens, passwords, or secret material.
- Keep only necessary personal data for matching workflows.
- Prefer masking/hashing where full identifiers are not operationally required.

Retention and deletion:
- Keep backup and retention windows aligned with MVP needs.
- Support user deletion/cleanup workflow for CV and related match artifacts.
- MVP deletion baseline: soft-delete CV and related match records.

## Secret Management

Secret source of truth:
- AWS Secrets Manager stores database credentials and third-party API keys.

Access controls:
- Services can read only the secrets they require.
- Avoid secrets in source code, container images, and committed env files.

Lifecycle:
- Retrieve secrets at startup (or controlled refresh where needed).
- Enable automated rotation where supported and manual periodic rotation otherwise.
- Audit secret access events and investigate unusual read patterns.

Operational rules:
- Rotate secrets immediately after suspected exposure.
- Revoke unused credentials and remove stale secret versions.

## Network Security

Segmentation model:
- Use VPC with public and private subnet separation.
- Keep ECS tasks and database in private subnets.
- Public ingress is limited to required edge/API components.
- Use multi-AZ subnet placement for resilience and fault isolation.

Traffic controls:
- Security groups allow only required inbound/outbound paths.
- Database access restricted to approved service security groups.
- NAT egress is used for required outbound calls (for example scraping, SES).
- Security groups enforce only approved service-to-service communication paths.

Perimeter protections:
- TLS certificates managed through ACM.
- Add WAF/rate limiting at the edge/API boundary as MVP hardening evolves.

Network baseline checks:
- No direct public database exposure.
- No broad "allow all" rules without explicit justification.

## Application Security Controls

Authentication and token handling:
- Validate JWT signature, issuer, audience/client, token_use, and expiry.
- Accept only access tokens for API authorization.
- Keep access tokens short-lived; use refresh flows only with Cognito.

Authorization and tenancy:
- Enforce per-user data ownership on every protected resource.
- Deny access to cross-user resources by default.

Input and output safety:
- Validate and sanitize all external inputs.
- Enforce request size and file-type limits for CV uploads.
- Use parameterized queries/ORM-safe patterns to reduce injection risk.

Async safety:
- Require idempotent message handlers.
- Preserve trace_id and job metadata across retries.
- Route repeated failures to DLQ for controlled replay.

Dependency and artifact security:
- Pin dependencies where practical and apply regular vulnerability updates.
- Scan container images and reject known critical vulnerabilities when feasible.

## Audit and Compliance Considerations

Auditability baseline:
- Keep structured logs for auth events, privileged actions, and key workflow transitions.
- Record who/what/when for CV upload, parsing, matching, and notification actions.
- Correlate logs across services using trace_id/request_id/job_id.

Privacy baseline:
- Follow data minimization principles for personal information.
- Avoid storing unnecessary sensitive content in logs and analytics.
- Restrict access to operational data by role.
- Keep an audit trail for CV uploads and optimization actions with timestamp and actor context.
- Do not persist raw CV content in logs.

MVP compliance posture:
- This is not a formal certification-ready program yet.
- Controls are aligned with common good practices (least privilege, encryption, audit logs, incident readiness).

## Incident Response Notes

Detection sources:
- API error/latency alerts.
- Queue backlog age and DLQ growth alerts.
- Authentication failure spikes.
- Infrastructure health signals from CloudWatch/Grafana stack.

Initial triage (first minutes):
1. Confirm impact and affected services.
2. Check recent deployments and configuration changes.
3. Inspect auth failures, queue health, and DB connectivity.
4. Contain blast radius (pause producers, scale consumers, or rollback if required).

Containment and recovery:
- Revoke/rotate secrets if compromise is suspected.
- Isolate failing integrations and replay DLQ only after root cause fix.
- Validate critical user flows after mitigation (login, upload, matches).

Post-incident:
- Document timeline, root cause, and corrective actions.
- Update runbooks, alerts, and preventive controls.

