# CV Match CDK Foundation

This project implements roadmap step 1: bootstrap-ready CDK foundation with stack boundaries and environment conventions.

## Foundation Boundaries

- network
- security
- shared-infra
- profile-service
- gateway-service

Stack naming follows this pattern:

- <appName>-<stage>-network
- <appName>-<stage>-security
- <appName>-<stage>-shared-infra
- <appName>-<stage>-profile-service
- <appName>-<stage>-gateway-service

Default values:

- appName: cv-match
- stage: dev

## Bootstrap Account and Region

Set your AWS profile and region, then bootstrap once per account/region:

```bash
export AWS_PROFILE=<default>
export AWS_REGION=<us-east-1>
aws sts get-caller-identity
cd infra/cdk
npx cdk bootstrap aws://$(aws sts get-caller-identity --query Account --output text)/$AWS_REGION
```

## Synthesize and Deploy (dev)

```bash
cd infra/cdk
npm run build # Compile Typescript
node dist/bin/cdk.js --version # Optional sanity check for built app entrypoint
npx cdk synth -c stage=dev -c appName=cv-match # Generate CloudFormation
npx cdk deploy --all -c stage=dev -c appName=cv-match # Upload infrastructure to AWS
```

For faster repeated runs, prefer the built-app workflow instead of `ts-node`:

```bash
cd infra/cdk
npm run synth -- -c stage=dev -c appName=cv-match
```

## Useful Commands

- npm run build
- npm run watch
- npm test
- npm run synth -- -c stage=dev -c appName=cv-match
- npm run diff -- -c stage=dev -c appName=cv-match
- npm run deploy:all -- -c stage=dev -c appName=cv-match
- npm run destroy:all -- -c stage=dev -c appName=cv-match
- npx cdk synth -c stage=dev -c appName=cv-match
- npx cdk diff --all -c stage=dev -c appName=cv-match
- npx cdk deploy --all -c stage=dev -c appName=cv-match
- npx cdk destroy --all -c stage=dev -c appName=cv-match

## Deployment Workflow

1. Set `AWS_PROFILE` and `AWS_REGION`.
2. Bootstrap the target account/region once with `npx cdk bootstrap`.
3. Synthesize and deploy the `dev` stage with the `stage` and `appName` context values.
4. For the current `dev` microservice flow, deploy `profile-service` first, resolve the emitted `ProfileServiceUrl`, and then deploy `gateway-service` with that URL passed as `profileServiceBaseUrl`.

If you only deploy one service, that is still supported for isolated validation. In that case, the service should not rely on a missing downstream endpoint unless you provide one explicitly.
