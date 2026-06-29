# Infrastructure CDK

## Purpose

Describe how the AWS CDK project is organized and how infrastructure is defined.

## CDK App Structure

- `bin/cdk.ts` is the executable entry point.
- `bin/foundation.ts` reads context and environment values, then wires the stacks together.
- `bin/conventions.ts` defines naming, tagging, and environment helpers.
- `lib/stacks/` contains the actual stack definitions only.

Recommended layout as the platform grows:

```text
bin/
	cdk.ts
	foundation.ts
	conventions.ts
lib/
	stacks/
		base-infra/
			network-stack.ts
			security-stack.ts
		shared-infra/
			data-stack.ts
		services/
			gateway-service-stack.ts
			profile-service-stack.ts
			cv-parser-service-stack.ts
			scraper-service-stack.ts
			matching-service-stack.ts
			notification-service-stack.ts
			cv-optimizer-service-stack.ts
```

Rule of thumb:

- keep `network`, `security`, and `shared-infra` as the shared foundation boundaries
- move real workloads into one stack per microservice when they need independent deploys or lifecycles

Test layout:

```text
tests/
	unit/
		cdk.test.ts
		network-stack.test.ts
		data-stack.test.ts
		gateway-service-stack.test.ts
	integration/
		# reserved for AWS-backed tests later
```

- `unit/` is for local synth and template assertions.
- `integration/` is for tests that may hit deployed AWS resources later.

First service example:

- `gateway-service-stack.ts` is the public API service stack, deployed behind an ALB and connected to the internal profile service URL.

Deployment flow for `dev`:

- When deploying both services together, deploy `profile-service` first, read its `ProfileServiceUrl` output, then pass that URL into the `gateway-service` stack as `profileServiceBaseUrl`.
- When deploying a single microservice for isolated validation, the stack should still synthesize and deploy independently, but the downstream URL must already be reachable or explicitly overridden if the service depends on it.
- Local Docker Compose remains the default for local development, while AWS deployments use the CDK/ECS path.

## Stacks

- `network` - VPC, subnets, and routing baseline.
- `security` - shared service-to-service and database access controls.
- `shared-infra` - RDS PostgreSQL, S3, and shared data resources.
- individual service stacks - runtime resources for each microservice.

Stack names follow this pattern:

- `<appName>-<stage>-network`
- `<appName>-<stage>-security`
- `<appName>-<stage>-shared-infra`
- `<appName>-<stage>-<service-name>`

## Shared Constructs

The current foundation uses stack classes directly and applies shared tags through `bin/conventions.ts`.

Standard tags:

- `project = cv-match`
- `environment = dev | staging | prod`
- `stack-boundary = network | security | shared-infra | <service-name>`
- `managed-by = aws-cdk`

## Environment Configuration

Environment values come from two places:

- CDK context values passed with `-c`, such as `stage` and `appName`.
- AWS environment variables provided by the shell or AWS profile, such as `AWS_PROFILE`, `AWS_REGION`, `CDK_DEFAULT_ACCOUNT`, and `CDK_DEFAULT_REGION`.

Default values:

- `appName = cv-match`
- `stage = dev`

Deployment examples:

```bash
npx cdk synth -c stage=dev -c appName=cv-match
npx cdk deploy --all -c stage=dev -c appName=cv-match
```

## Deployment Workflow

1. Set `AWS_PROFILE` and `AWS_REGION`.
2. Bootstrap the target account/region once with `npx cdk bootstrap`.
3. Synthesize and deploy the `dev` stage with the `stage` and `appName` context values.

## Current Dev Baseline

- `network-stack.ts` provisions the VPC and subnet tiers with `natGateways: 0` for cost control in `dev`.
- `security-stack.ts` provisions shared application and database security groups.
- `data-stack.ts` provisions a cost-sensitive `RDS PostgreSQL` instance in isolated subnets.
- `data-stack.ts` provisions a private versioned S3 bucket for CV uploads.
- `gateway-service-stack.ts` consumes the shared VPC and runs ECS tasks in private subnets behind a public ALB.

## Network Egress in Dev

- Default `dev` baseline keeps NAT disabled to reduce recurring cost.
- Private workloads requiring outbound internet should trigger an explicit network update to re-enable NAT (or introduce specific VPC endpoints).

## IAM and Permissions Boundaries

The foundation assumes the deploy role or profile can create and manage the resources in the selected account/region. IAM permission boundaries are not defined yet.
