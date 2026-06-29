import { Environment, Tags } from 'aws-cdk-lib';
import { IConstruct } from 'constructs';

export type DeploymentStage = 'dev' | 'staging' | 'prod';

export interface FoundationConfig {
  appName: string;
  stage: DeploymentStage;
  env: Environment;
}

export function getStage(value?: string): DeploymentStage {
  if (!value) {
    return 'dev';
  }

  if (value === 'staging' || value === 'prod' || value === 'dev') {
    return value;
  }

  throw new Error(`Invalid deployment stage: ${value}. Expected one of dev, staging, prod.`);
}

export function getEnvironment(): Environment {
  const account = process.env.CDK_DEFAULT_ACCOUNT ?? process.env.AWS_ACCOUNT_ID;
  const region = process.env.CDK_DEFAULT_REGION ?? process.env.AWS_REGION;

  if (!account || !region) {
    throw new Error(
      'Missing AWS account/region for CDK. Set AWS profile/region, then run: cdk bootstrap aws://ACCOUNT/REGION',
    );
  }

  return { account, region };
}

export function stackId(config: FoundationConfig, boundary: string): string {
  return `${config.appName}-${config.stage}-${boundary}`;
}

export function applyConventions(config: FoundationConfig, boundary: string, resource: IConstruct): void {
  Tags.of(resource).add('project', config.appName);
  Tags.of(resource).add('environment', config.stage);
  Tags.of(resource).add('stack-boundary', boundary);
  Tags.of(resource).add('managed-by', 'aws-cdk');
}