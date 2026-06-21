# Scripts

This folder contains the root local orchestration scripts.


## Recommended Testing Local Flow

**Check Unit && Component tests**
```bash
./scripts/deploy-local.sh up test services
./scripts/test-local.sh services
./scripts/deploy-local.sh down
```

**Check Cross Service tests**
```bash
./scripts/deploy-local.sh up test cross-service
./scripts/test-local.sh cross-service
./scripts/deploy-local.sh down
```



## deploy-local.sh

Use this script from the repository root to manage either service-local stacks or the cross-service stack.

Basic usage:

```bash
./scripts/deploy-local.sh [up|down] [runtime|test] [services|cross-service]
```

Examples:

```bash
./scripts/deploy-local.sh
./scripts/deploy-local.sh up runtime services
./scripts/deploy-local.sh up test services
./scripts/deploy-local.sh up test cross-service
./scripts/deploy-local.sh down test
```

Notes:

- default action is `up`
- default mode is `test`
- default scope is `services`
- `services` scope delegates to each service `scripts/deploy-local.sh`
- `cross-service` scope uses root `docker-compose.yml`

## test-local.sh

Use this script from the repository root to run tests in one explicit scope.

Basic usage:

```bash
./scripts/test-local.sh [services|cross-service]
```

Examples:

```bash
./scripts/test-local.sh
./scripts/test-local.sh services
./scripts/test-local.sh cross-service
```

Notes:

- only two scopes are accepted: `services` and `cross-service`
- `services` delegates to each service `scripts/test-local.sh`
- `cross-service` runs `tests/cross-service/run-cross-service.sh`
- `cross-service` requires the cross-service stack to be running first
