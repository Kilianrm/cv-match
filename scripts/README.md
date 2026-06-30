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
./scripts/dev.sh --action test
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

## dev.sh

Use this script from the repository root to orchestrate AWS dev infrastructure deployment and infrastructure tests.

Basic usage:

```bash
./scripts/dev.sh --action <deploy|destroy|test> [--stack <stack>] [--suite <suite>]
```

Examples:

```bash
./scripts/dev.sh --action deploy --stack gateway
./scripts/dev.sh --action deploy --stack full
./scripts/dev.sh --action destroy --stack profile
./scripts/dev.sh --action destroy --stack full
./scripts/dev.sh --action test
./scripts/dev.sh --action test --suite infra
./scripts/dev.sh --action test --stack full --suite smoke
```

Notes:

- `test --suite infra` runs CDK unit tests (no deployed infra required)
- `test --suite smoke` validates against already deployed infra and requires `--stack`
- `--stack` accepts `network`, `security`, `auth`, `data`, `gateway`, `profile`, or `full`
- `--suite` accepts `infra` or `smoke` and is valid only with `--action test`
- `--action deploy` requires `--stack`
- `--action destroy` requires `--stack`

## deploy-dev.sh

Compatibility wrapper for `./scripts/dev.sh`.

Basic usage:

```bash
./scripts/deploy-dev.sh [--destroy|--destroy-all]
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
- it runs frontend env sync from `scripts/support/sync-frontend-env-dev.sh`
- it preserves existing gateway env values if they are already present in the frontend env file


## test-dev.sh

Compatibility wrapper for `./scripts/dev.sh --action test`.

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

- accepts only help flags (`-h`, `--help`, `help`)

