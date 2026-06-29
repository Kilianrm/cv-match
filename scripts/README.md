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

**Check Infrastructure local validation**
```bash
./scripts/test-dev.sh
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
- `cross-service` runs all tests under `tests/cross-service` directly via `python3 -m pytest`
- `cross-service` requires the cross-service stack to be running first

## deploy-dev.sh

Use this script from the repository root to orchestrate AWS dev infrastructure deployment.

Basic usage:

```bash
./scripts/deploy-dev.sh [--destroy|--destroy-all]
```

Examples:

```bash
./scripts/deploy-dev.sh
./scripts/deploy-dev.sh --destroy
./scripts/deploy-dev.sh --destroy-all
```

## support/deploy-frontend-auth-dev.sh

Use this support script when you want conceptual local frontend testing with AWS `dev` authentication only.

Basic usage:

```bash
./scripts/support/deploy-frontend-auth-dev.sh [--destroy|--destroy-all]
```

Examples:

```bash
./scripts/support/deploy-frontend-auth-dev.sh
./scripts/support/deploy-frontend-auth-dev.sh --destroy
./scripts/support/deploy-frontend-auth-dev.sh --destroy-all
```

Notes:

- this is a support-only conceptual testing workflow
- it forces `DEPLOY_STACKS=network,auth`
- it deploys directly from `infra/cdk` instead of using the broader infra workflow
- it runs auth-only frontend env sync from `scripts/support/sync-frontend-auth-dev.sh`
- it preserves existing gateway env values if they are already present in the frontend env file


## test-dev.sh

Use this script from the repository root to run infrastructure validation for the dev workflow.

Basic usage:

```bash
./scripts/test-dev.sh
```

Examples:

```bash
./scripts/test-dev.sh
./scripts/test-dev.sh --help
```

Notes:

- delegates to `infra/scripts/test-infra.sh`
- runs CDK unit tests from `infra/cdk`
- accepts only help flags (`-h`, `--help`, `help`)

