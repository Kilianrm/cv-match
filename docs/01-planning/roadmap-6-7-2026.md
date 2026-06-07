# Roadmap

## Purpose

Define a short, execution-first plan: document and implement in iterations for the next two services.

## Scope

- Focus services: Profile Service and CV Parser Service.
- Work mode: iterate between documentation and implementation.
- Environment strategy: local first with tests, then deploy to AWS.

## Working Method (Iterative)

For each service iteration:
1. Update only the necessary docs (API, sequence, data behavior).
2. Implement the feature in code.
3. Add or update tests (unit + integration).
4. Run locally and validate end-to-end.
5. Move to the next iteration.

## Phase 1: Local Implementation

Goals:
- Implement and validate Profile Service and CV Parser Service locally.
- Cover flows already designed (upload, parse, and manual profile update).
- Keep parser and profile integration working through internal API.

Local deliverables:
- Services run locally with database, queue, and object storage.
- Passing tests for core flows.
- Stable internal contract between CV Parser and Profile Service.

## Phase 2: AWS Deployment (After Local Validation)

Goals:
- Deploy the same validated flows to AWS dev.
- Keep cloud usage minimal and controlled.

AWS deliverables:
- Profile Service and CV Parser Service deployed in dev.
- End-to-end smoke test passing in AWS.
- Cost checks in place (budget alarm + cleanup routine).

## Milestones

- M1: Local setup ready for Profile + Parser.
- M2: Core local flows implemented and tested.
- M3: AWS dev deployment completed.
- M4: AWS end-to-end validation completed.

## Cost Guardrails

- Local is the default environment for daily development.
- AWS is only for validation windows.
- Destroy or stop nonessential dev resources after each validation session.

## Phase 4: Implement Flow 05 (Manual Profile Edit) (Week 2-3)

Objectives:
- Implement user profile update endpoint.
- Validate editable fields and return field-level errors.
- Keep this flow synchronous and simple in MVP.

Deliverables:
- Working endpoint: PUT /api/v1/profile.
- Integration test for valid update and invalid payload.
- Profile completion percent recalculation on update.

## Phase 5: Cloud Validation (Low-Cost Mode) (Week 3)

Objectives:
- Deploy only the minimum stack to AWS dev for architecture validation.
- Validate Cognito + API Gateway + one async path end-to-end.
- Measure costs and shut down nonessential resources after tests.

Deliverables:
- Short-lived AWS dev deployment script.
- Cost report after validation run.
- Runbook: start validation window and shutdown checklist.

## Phase 6: Hardening and Release Readiness (Week 4)

Objectives:
- Add observability minimums, retries, and DLQ handling.
- Freeze MVP scope and finalize acceptance tests.
- Prepare first public demo/release candidate.

Deliverables:
- Core dashboards and alert rules.
- End-to-end test report for flows 03, 04, and 05.
- MVP release checklist signed off.

## Milestones

- M1: Local stack running (API + Profile + Parser + DB + Queue + Storage).
- M2: Flow 03 complete (upload + validation + enqueue).
- M3: Flow 04 complete (consume + parse + sync profile update).
- M4: Flow 05 complete (manual profile editing).
- M5: AWS low-cost validation complete.
- M6: MVP release-readiness sign-off.

## Cloud Cost Control Plan

Rules:
- Local-first by default for daily development.
- AWS environments are ephemeral: create only during validation windows, then destroy.
- Prefer cheapest service classes in dev and disable multi-AZ/nonessential redundancy.
- Enforce budget alarms and hard spending thresholds.

Practical controls:
- One shared dev environment only (no parallel personal environments).
- Scheduled stop/destroy for nonproduction resources.
- Log retention set to low days for dev.
- Use local emulation for SQS/S3 where possible.

## Risks and Dependencies

Key risks:
- Scope growth can delay the first shippable MVP.
- Contract drift between sequence diagrams and implementation.
- Parser quality variance due to PDF format diversity.
- Hidden cloud costs from idle resources.

Dependencies:
- Stable local Docker-based environment.
- AWS account with budget alarms configured before Phase 5.
- Stable contract for profile internal API used by parser.

## Open Questions

- Should profile update endpoint be PUT /profile or PATCH /profile for MVP?
- Do we trigger rematching immediately after manual profile update or leave it manual for MVP?
- Which local stack should be standard: LocalStack vs MinIO + queue emulator?