# CV Match CDK Foundation

This project implements roadmap step 1: bootstrap-ready CDK foundation with stack boundaries and environment conventions.

## Foundation Boundaries

- network
- data
- services
- optional observability

Stack naming follows this pattern:

- <appName>-<stage>-network
- <appName>-<stage>-data
- <appName>-<stage>-services
- <appName>-<stage>-observability

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
npx cdk synth -c stage=dev -c appName=cv-match # Generate CloudFormation
npx cdk deploy --all -c stage=dev -c appName=cv-match # Upload infrastructure to AWS
```

Enable optional observability boundary:

```bash
npx cdk deploy --all -c stage=dev -c appName=cv-match -c enableObservability=true
```

## Useful Commands

- npm run build
- npm run watch
- npm test
- npx cdk synth -c stage=dev -c appName=cv-match
- npx cdk diff --all -c stage=dev -c appName=cv-match
- npx cdk deploy --all -c stage=dev -c appName=cv-match
- npx cdk destroy --all -c stage=dev -c appName=cv-match
