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
		network-stack.ts
		data-stack.ts
		observability-stack.ts
		services-stack.ts
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

- keep `network` and `data` as shared infrastructure stacks
- keep `services-stack.ts` only if it stays a thin grouping boundary
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

## Stacks

- `network` - VPC, subnets, routing, and security group baseline.
- `data` - RDS PostgreSQL, S3, and shared data resources.
- `services` - thin grouping boundary for shared service wiring, if needed.
- individual service stacks - runtime resources for each microservice.
- `observability` - optional alarms, dashboards, and log configuration.

Stack names follow this pattern:

- `<appName>-<stage>-network`
- `<appName>-<stage>-data`
- `<appName>-<stage>-services`
- `<appName>-<stage>-observability`

## Shared Constructs

The current foundation uses stack classes directly and applies shared tags through `bin/conventions.ts`.

Standard tags:

- `project = cv-match`
- `environment = dev | staging | prod`
- `stack-boundary = network | data | services | observability`
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
4. Enable `observability` only when needed with `-c enableObservability=true`.

## Current Dev Baseline

- `network-stack.ts` provisions the VPC, subnets, NAT strategy, and shared security groups.
- `data-stack.ts` provisions a cost-sensitive `RDS PostgreSQL` instance in isolated subnets.
- `data-stack.ts` provisions a private versioned S3 bucket for CV uploads.
- `gateway-service-stack.ts` consumes the shared VPC and runs ECS tasks in private subnets behind a public ALB.

## IAM and Permissions Boundaries

The foundation assumes the deploy role or profile can create and manage the resources in the selected account/region. IAM permission boundaries are not defined yet.
