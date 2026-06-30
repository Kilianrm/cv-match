# Profile Service

Profile-service is the internal owner of user profile data and CV files.
It is mainly consumed by gateway-service, which exposes client/user-facing endpoints and forwards profile-related operations to this service.

## Quickstart (Local)

Run from this folder: services/profile-service

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

