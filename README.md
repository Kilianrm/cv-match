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

## Prerequisites

Before using the root Makefile workflow, complete these steps:

1. Bootstrap your AWS account and region for CDK:
	1. Follow the bootstrap guidance in [infra/cdk/README.md](infra/cdk/README.md).
2. Configure your local frontend setup:
	1. Follow [frontend/README.md](frontend/README.md).
3. Configure AWS credentials on your machine:
	1. Make sure your AWS CLI credentials/profile are set and valid for the target account.
4. Prepare the root dev environment file:
	1. Run `cp .env.dev.example .env.dev`.

After these prerequisites are complete, you are ready to use the Makefile commands.

## Local Development

Use the root Makefile as the main entry point.

## Main Commands (Makefile)

Show available commands:

```bash
make help
```

### Local Environment

Bring up selected local services:

```bash
make local-up STACK=gateway
make local-up STACK=profile
make local-up STACK=cv-parser
make local-up STACK=gateway,profile
make local-up STACK=gateway,profile,cv-parser
make local-up STACK=full
make local-up STACK=full SKIP_FRONTEND=true
```

Tear down selected local services:

```bash
make local-down STACK=gateway
make local-down STACK=profile
make local-down STACK=cv-parser
make local-down STACK=gateway,profile
make local-down STACK=gateway,profile,cv-parser
make local-down STACK=full
```

Run local tests:

```bash
make local-test STACK=gateway SUITE=unit
make local-test STACK=cv-parser SUITE=unit
make local-test STACK=gateway,profile SUITE=unit
make local-test STACK=gateway,profile,cv-parser SUITE=unit
make local-test STACK=full SUITE=integration
```

Notes:

- `STACK` is required for `local-up`, `local-down`, and `local-test`.
- For service-level stacks (`gateway`, `profile`, `cv-parser`, or comma-separated), use `SUITE=unit`.
- For `STACK=full`, use `SUITE=integration`.

### Dev (AWS) Environment

Deploy selected stacks:

```bash
make dev-deploy STACK=network
make dev-deploy STACK=network,security,auth
make dev-deploy STACK=full
```

Destroy selected stacks:

```bash
make dev-destroy STACK=profile
make dev-destroy STACK=network,security,auth
make dev-destroy STACK=full
```

Manual support actions:

```bash
make dev-bootstrap-db
make dev-test-bootstrap-db
make dev-sync-frontend
```

- `make dev-bootstrap-db`: initializes the deployed dev database with seed/reference data.
- `make dev-test-bootstrap-db`: validates deployed bootstrap DB data consistency.
- `make dev-sync-frontend`: links local frontend configuration to the deployed cloud backend (auth + gateway endpoints).

Run infra or smoke tests:

```bash
make dev-test SUITE=infra
make dev-test STACK=full SUITE=smoke
```

Notes:

- `STACK` is required for `dev-deploy` and `dev-destroy`.
- `dev-test SUITE=smoke` requires `STACK`.
- `dev-test SUITE=smoke` runs only `smoke-aws-deployed` checks (bootstrap DB validation is separate).
- On deploy, if `.env.dev` is missing and `.env.dev.example` exists, `scripts/dev.sh` creates `.env.dev` automatically.

The Makefile delegates to the scripts under `scripts/` and keeps all orchestration and validation logic centralized there.

For deeper script-level details, see:

- [Local Run and Test Instructions](scripts/README.md)

## Documentation

- Planning and roadmaps: [docs/01-planning](docs/01-planning)
- Architecture and design: [docs/02-architecture](docs/02-architecture)
- Design: [docs/03-design](docs/03-design)
- Implementation notes: [docs/04-implementation](docs/04-implementation)
