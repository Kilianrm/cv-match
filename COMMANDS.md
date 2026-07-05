# Dev Command Cheat Sheet

Quick reference for day-to-day development commands.

---

## Local Environment (`deploy-local.sh`)

### Positional arguments

```
./scripts/deploy-local.sh [up|down] [runtime|test] [services|cross-service]
```

| Argument | Values | Default |
|---|---|---|
| action | `up` \| `down` | `up` |
| mode | `runtime` \| `test` | `test` |
| scope | `services` \| `cross-service` | `services` |

### Common calls

```bash
# Start all services in test mode (most common)
./scripts/deploy-local.sh

# Start services explicitly
./scripts/deploy-local.sh up test services

# Start services in runtime mode (no test containers)
./scripts/deploy-local.sh up runtime services

# Start cross-service stack (for e2e tests)
./scripts/deploy-local.sh up test cross-service

# Tear down everything
./scripts/deploy-local.sh down

# Tear down cross-service stack
./scripts/deploy-local.sh down test cross-service
```

### Environment variable overrides

```bash
# Skip port conflict check
SKIP_PORT_CHECK=true ./scripts/deploy-local.sh

# Don't auto-kill processes on conflicting ports
AUTO_FREE_PORTS=false ./scripts/deploy-local.sh

# Remove volumes on teardown
REMOVE_VOLUMES=true ./scripts/deploy-local.sh down

# Skip pre-clean before bringing up containers
PRE_CLEAN_BEFORE_UP=false ./scripts/deploy-local.sh up
```

---

## Local Test Runs (`test-local.sh`)

```bash
# Run unit/component tests for all services (default)
./scripts/test-local.sh

./scripts/test-local.sh services

# Run cross-service / e2e tests (requires cross-service stack to be up)
./scripts/test-local.sh cross-service
```

---

## Full Local Test Workflows

```bash
# Unit & component tests
./scripts/deploy-local.sh up test services
./scripts/test-local.sh services
./scripts/deploy-local.sh down

# Cross-service / e2e tests
./scripts/deploy-local.sh up test cross-service
./scripts/test-local.sh cross-service
./scripts/deploy-local.sh down
```

---

## AWS Dev Workflow (`dev.sh`)

### Flags

```bash
./scripts/dev.sh --action deploy --stack gateway
./scripts/dev.sh --action deploy --stack full
./scripts/dev.sh --action destroy --stack profile
./scripts/dev.sh --action destroy --stack full
```

### Environment variable overrides

```bash
# Change app/stage/region
APP_NAME=my-app ./scripts/dev.sh --action deploy --stack full
STAGE=staging AWS_REGION=eu-west-1 ./scripts/dev.sh --action deploy --stack full
```

Only `APP_NAME`, `STAGE`, and `AWS_REGION` are accepted environment variables by `./scripts/dev.sh`.

---

## Infrastructure Tests

```bash
./scripts/dev.sh --action bootstrap
./tests/integration/bootstrap-dev-db.test.sh
./scripts/dev.sh --action test
./scripts/dev.sh --action test --suite infra
./scripts/dev.sh --action test --suite smoke --stack full
```
