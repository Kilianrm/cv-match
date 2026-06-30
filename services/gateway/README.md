# Gateway Service

Gateway-service is the client-facing API entrypoint.
It receives user/client requests, handles auth/session flow, and orchestrates access to multiple internal capabilities across the platform.
It is the main entry point for many endpoint groups in the system, including profile-related operations and other public API routes.

## Quickstart (Local)

Run from this folder: services/gateway-service

1. Deploy local test stack:

```bash
./scripts/deploy-local.sh up test
```

2. Run local tests:

```bash
./scripts/test-local.sh
```

3. Stop local stack:

```bash
./scripts/deploy-local.sh down test
```
