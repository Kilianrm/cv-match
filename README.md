# CV Match

CV Match is a local-first microservice project for CV/profile workflows.

This README focuses on local development and testing.

## Recommended Flow (Use This)

Use this flow for daily work:

1. Deploy service-local test stacks and run `services` scope.
2. Deploy cross-service stack and run `cross-service` scope.
3. Tear down stacks when finished.

```bash
./scripts/deploy-local.sh up test services
./scripts/test-local.sh services

./scripts/deploy-local.sh up test cross-service
./scripts/test-local.sh cross-service

./scripts/deploy-local.sh down test services
./scripts/deploy-local.sh down test cross-service
```

Only two scopes are supported: `services` and `cross-service`.

## Prerequisites

- Docker + Docker Compose v2
- Bash shell

## Quick Start (Local)

Expected local flow:

- Deploy a service in `test` mode.
- Run that service's local tests inside its running test container.
- Repeat for the next service.

### 1) Deploy profile-service in test mode

```bash
cd services/profile-service
./scripts/deploy-local.sh up test
```

### 2) Run profile-service tests

```bash
cd services/profile-service
./scripts/test-local.sh
```

### 3) Deploy gateway-service in test mode

```bash
cd services/gateway-service
./scripts/deploy-local.sh up test
```

### 4) Run gateway-service tests

```bash
cd services/gateway-service
./scripts/test-local.sh
```

## What Must Be Deployed Before Tests

Service-local tests are not auto-deploying containers. They run against already-running test stacks.

- For `services/profile-service/scripts/test-local.sh`:
	- required deployment: `services/profile-service/scripts/deploy-local.sh up test`
	- tests run: profile-service unit/integration tests in the profile-service container

- For `services/gateway-service/scripts/test-local.sh`:
	- required deployment: `services/gateway-service/scripts/deploy-local.sh up test`
	- tests run: gateway-service unit/integration tests in the gateway-service container

If the container is not running, test scripts exit with an error and tell you which deploy command to run.

Cross-service tests are separate and expect a multi-service local environment.

## Deploy Script Behavior

For each service, `scripts/deploy-local.sh` supports:

```bash
./scripts/deploy-local.sh [up|down] [runtime|test]
```

Defaults:

- action: `up`
- mode: `runtime`

Examples:

```bash
./scripts/deploy-local.sh
./scripts/deploy-local.sh up test
./scripts/deploy-local.sh down runtime
REMOVE_VOLUMES=true ./scripts/deploy-local.sh down test
```

Important behavior:

- Before `up`, the script cleans both `*-runtime` and `*-test` projects for that service family.
- This avoids port conflicts when switching modes.

## Test Script Behavior

For each service, `scripts/test-local.sh`:

- expects the `test` stack to already be running
- executes `pytest` via `docker compose exec` inside the running service container
- fails fast with a clear message if the service container is not running

If needed, run:

```bash
./scripts/deploy-local.sh up test
./scripts/test-local.sh
```

## Health Endpoints

- profile-service: `http://localhost:8080/health`
- gateway-service: `http://localhost:8000/health`

## Stop Local Stacks

```bash
cd services/profile-service
./scripts/deploy-local.sh down test

cd ../gateway-service
./scripts/deploy-local.sh down test
```

## Cross-Service E2E Tests

Cross-service tests live in `tests/cross-service`.

- Script: `tests/cross-service/test.sh`
- Preferred script: `tests/cross-service/run-cross-service.sh`
- Main suite: `tests/cross-service/test_e2e.py`
- Negative suite: `tests/cross-service/test_e2e_negative.py`

`tests/cross-service/test.sh` remains as a compatibility wrapper.

For cross-service local execution, ensure both service stacks are up in compatible local mode before running the cross-service script.

Preferred setup from repository root:

```bash
./scripts/deploy-local.sh up test integration
./scripts/test-local.sh cross-service
```

