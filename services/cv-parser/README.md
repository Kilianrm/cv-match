# CV Parser Service

Notes:

- Queue ownership is logical (resource-level): `cv-parser-queue` and `cv-parser-dlq` belong to this service.
- You do not need a separate LocalStack per service; one LocalStack instance can emulate S3 and SQS for multiple services.
- Local deploy uses LocalStack init hooks (`scripts/localstack/init`) to bootstrap parser-owned queue resources and the profile CV bucket automatically.

Local development:

1. Bring up runtime stack:

```bash
./scripts/deploy-local.sh up runtime
```

2. Run tests (requires test stack up):

```bash
./scripts/deploy-local.sh up test
./scripts/test-local.sh
```

3. Tear down stack:

```bash
./scripts/deploy-local.sh down runtime
```
