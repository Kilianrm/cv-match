import { App, Environment } from 'aws-cdk-lib';
import { NetworkStack } from '../lib/stacks/base/network';
import { SecurityStack } from '../lib/stacks/base/security';
import { AuthStack } from '../lib/stacks/shared/auth';
import { ComputeStack } from '../lib/stacks/shared/compute';
import { DataStack } from '../lib/stacks/shared/data';
import { GatewayServiceStack } from '../lib/stacks/services/gateway';
import { ProfileServiceStack } from '../lib/stacks/services/profile';
import { FoundationConfig, getEnvironment, getStage, stackId } from './conventions';

export interface FoundationAppOptions {
  stage?: string;
  appName?: string;
  env?: Environment;
  useSharedSecurity?: boolean;
  publicDatabaseAccess?: boolean;
  publicDatabaseAccessCidr?: string;
  profileServiceBaseUrl?: string;
  localFrontendBaseUrl?: string;
  cognitoDomainPrefix?: string;
}

function parseOptionalBoolean(value: string | undefined): boolean | undefined {
  if (value === undefined) {
    return undefined;
  }

  if (value === 'true') {
    return true;
  }

  if (value === 'false') {
    return false;
  }

  throw new Error(`Invalid boolean value: ${value}. Expected true or false.`);
}

export function deployFoundation(app: App, options: FoundationAppOptions = {}) {
  const config: FoundationConfig = {
    appName: options.appName ?? 'cv-match',
    stage: getStage(options.stage),
    env: options.env ?? getEnvironment(),
  };

  const useSharedSecurity = options.useSharedSecurity ?? true;
  const publicDatabaseAccess = options.publicDatabaseAccess ?? false;
  const publicDatabaseAccessCidr = options.publicDatabaseAccessCidr;
  const profileServiceBaseUrl = options.profileServiceBaseUrl ?? 'http://profile-service:8080';
  const localFrontendBaseUrl = options.localFrontendBaseUrl;
  const cognitoDomainPrefix = options.cognitoDomainPrefix;

  if (publicDatabaseAccess && config.stage !== 'dev') {
    throw new Error('publicDatabaseAccess is only allowed for dev stage.');
  }

  if (publicDatabaseAccess && !publicDatabaseAccessCidr) {
    throw new Error('publicDatabaseAccessCidr is required when publicDatabaseAccess is enabled.');
  }

  const network = new NetworkStack(app, stackId(config, 'network'), {
    env: config.env,
    foundation: config,
    description: 'Base infrastructure stack for networking resources.',
  });

  const security = useSharedSecurity
    ? new SecurityStack(app, stackId(config, 'security'), {
        env: config.env,
        foundation: config,
        vpc: network.vpc,
        allowDatabasePublicAccess: publicDatabaseAccess,
        databasePublicAccessCidr: publicDatabaseAccessCidr,
        description: 'Base infrastructure stack for shared security controls.',
      })
    : undefined;

  const compute = new ComputeStack(app, stackId(config, 'compute'), {
    env: config.env,
    foundation: config,
    vpc: network.vpc,
    description: 'Shared compute stack for ECS cluster resources.',
  });

  const data = new DataStack(app, stackId(config, 'data'), {
    env: config.env,
    foundation: config,
    vpc: network.vpc,
    databaseSecurityGroup: security?.databaseSecurityGroup,
    allowSelfManagedSecurityGroup: !useSharedSecurity,
    publicDatabaseAccess,
    publicDatabaseAccessCidr,
    description: 'Shared infrastructure stack for storage and data resources.',
  });

  const auth = new AuthStack(app, stackId(config, 'auth'), {
    env: config.env,
    foundation: config,
    localFrontendBaseUrl,
    cognitoDomainPrefix,
    description: 'Shared authentication stack for Cognito user pool and Hosted UI.',
  });

  const profileService = new ProfileServiceStack(app, stackId(config, 'profile'), {
    env: config.env,
    foundation: config,
    vpc: network.vpc,
    cluster: compute.cluster,
    databaseSecret: data.database.secret!,
    databaseHost: data.database.instanceEndpoint.hostname,
    cvBucket: data.cvBucket,
    securityGroups: security ? [security.serviceSecurityGroup] : undefined,
    description: 'Profile service stack for user profile and CV workflows.',
  });

  const gatewayService = new GatewayServiceStack(app, stackId(config, 'gateway'), {
    env: config.env,
    foundation: config,
    vpc: network.vpc,
    cluster: compute.cluster,
    profileServiceBaseUrl,
    cognitoClientId: auth.userPoolClient.userPoolClientId,
    jwksUrl: auth.jwksUrl,
    description: 'Gateway service stack for the public API.',
  });

  data.addDependency(network);
  if (security) {
    data.addDependency(security);
  }
  compute.addDependency(network);
  auth.addDependency(network);
  profileService.addDependency(network);
  profileService.addDependency(compute);
  if (security) {
    profileService.addDependency(security);
  }
  profileService.addDependency(data);
  gatewayService.addDependency(network);
  gatewayService.addDependency(compute);
  gatewayService.addDependency(auth);
  gatewayService.addDependency(profileService);
  if (security) {
    gatewayService.addDependency(security);
  }

  return { network, security, compute, data, auth, profileService, gatewayService, config };
}


export function deployFoundationFromContext(app: App) {
  const stage = app.node.tryGetContext('stage') as string | undefined;
  const appName = app.node.tryGetContext('appName') as string | undefined;
  const useSharedSecurityValue = app.node.tryGetContext('useSharedSecurity') as string | undefined;
  const useSharedSecurity = parseOptionalBoolean(useSharedSecurityValue);
  const publicDatabaseAccessValue = app.node.tryGetContext('publicDatabaseAccess') as string | undefined;
  const publicDatabaseAccess = parseOptionalBoolean(publicDatabaseAccessValue);
  const publicDatabaseAccessCidr = app.node.tryGetContext('publicDatabaseAccessCidr') as string | undefined;
  const profileServiceBaseUrl = app.node.tryGetContext('profileServiceBaseUrl') as string | undefined;
  const localFrontendBaseUrl = app.node.tryGetContext('localFrontendBaseUrl') as string | undefined;
  const cognitoDomainPrefix = app.node.tryGetContext('cognitoDomainPrefix') as string | undefined;

  return deployFoundation(app, {
    stage,
    appName,
    useSharedSecurity,
    publicDatabaseAccess,
    publicDatabaseAccessCidr,
    profileServiceBaseUrl,
    localFrontendBaseUrl,
    cognitoDomainPrefix,
  });
}