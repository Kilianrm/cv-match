# CV Match

CV Match is a local-first, event-driven microservices platform for CV parsing, profile workflows, and weighted matching, exposing both backend APIs and a frontend application, with CI/CD, monitoring and observability, scalability, and security as core delivery principles.

## Project Status

This project is currently in active development.

- Core microservices foundations are in place.
- Local deploy/test orchestration is available for service-local and cross-service validation.
- AWS CDK infrastructure foundations are being implemented and validated incrementally.

Expect ongoing changes in architecture, automation scripts, and documentation while roadmap milestones are completed.

## Current Scope

- Gateway and profile service workflows.
- CV parsing and profile lifecycle operations.
- Cross-service end-to-end checks for critical user journeys.
- Infrastructure as Code foundations for AWS deployment.

## Local Development

For local deploy and test commands, use the root scripts documentation:

- [Local Run and Test Instructions](scripts/README.md)

## Documentation

- Planning and roadmaps: [docs/01-planning](docs/01-planning)
- Architecture and design: [docs/02-architecture](docs/02-architecture)
- Design: [docs/03-design](docs/03-design)
- Implementation notes: [docs/04-implementation](docs/04-implementation)
