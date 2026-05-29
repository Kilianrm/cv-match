# Deployment

## Purpose

Describe how CV Match services are deployed and operated across environments.

Scope of this document:
- Deployment and release operations (environments, rollout, rollback, CI/CD behavior)
- Practical execution guidance for a local-first personal project

## Environments

CV Match uses a staged environment strategy that starts simple and scales only when needed.

| Environment | Purpose | Deployment Trigger |
|---|---|---|
| Local | Primary development and fast feedback | Manual from local machine |
| AWS Dev (Personal) | Cloud integration validation | Manual CDK deploy from local |
| Optional Staging (Future) | Pre-release confidence checks | Manual with approval gate |
| Optional Production (Future) | User-facing release | Manual with stricter approvals |

Environment principles:
- Prefer local validation first, then validate cloud behavior in AWS Dev
- Keep operational overhead low during MVP
- Add new environments only when they reduce real release risk


## CI/CD Flow

CV Match follows a local-first workflow with gradual CI/CD adoption.

Local-first baseline:
1. Develop and test locally
2. Run local quality checks before push (lint, tests, format checks)
3. Deploy manually to AWS Dev from local machine with CDK
4. Run smoke checks after deploy

Minimal CI (first automation step):
- Use GitHub Actions for validation on pull request and push to main
- Run the same checks used locally
- Do not auto-deploy in the first stage

CD option (second step):
- Keep deployment manual, but allow workflow_dispatch for controlled releases
- Use environment approvals for staging/production-like environments
- Use OIDC for AWS authentication to avoid long-lived keys

Deployment checklist:

Pre-deploy:
- Local checks pass
- CI checks pass
- Required secrets/config present
- Rollback target identified

Post-deploy:
- Health endpoint success
- Critical flows pass smoke tests (auth, queue processing, database access)
- Error metrics remain within normal range

Implementation reference:
- CDK structure and conventions: [docs/04-implementation/infrastructure-cdk.md](../04-implementation/infrastructure-cdk.md)

## Rollback Strategy

Rollback is manual-first in MVP and focused on quick restoration of the last known good version.

Rollback triggers:
- Health checks fail after deployment
- Error rate spike persists beyond acceptable threshold
- Critical user flow fails (login, upload, match retrieval)

Rollback by unit:
- Frontend: redeploy previous static artifact version
- API/workers: redeploy previous known-good image tag or task definition
- Infrastructure: revert CDK change and deploy stable revision

Operational rules:
- Run smoke checks after rollback
- Record incident summary and root cause before next deployment attempt