import { App, Environment } from 'aws-cdk-lib';
import { DataStack } from '../lib/stacks/data-stack';
import { NetworkStack } from '../lib/stacks/network-stack';
import { ObservabilityStack } from '../lib/stacks/observability-stack';
import { GatewayServiceStack } from '../lib/stacks/services/gateway-service-stack';
import { ServicesStack } from '../lib/stacks/services-stack';
import { FoundationConfig, getEnvironment, getStage, stackId } from './conventions';

export interface FoundationAppOptions {
  stage?: string;
  appName?: string;
  enableObservability?: boolean;
  env?: Environment;
}

export function deployFoundation(app: App, options: FoundationAppOptions = {}) {
  const config: FoundationConfig = {
    appName: options.appName ?? 'cv-match',
    stage: getStage(options.stage),
    env: options.env ?? getEnvironment(),
  };

  const network = new NetworkStack(app, stackId(config, 'network'), {
    env: config.env,
    foundation: config,
    description: 'Boundary stack for networking resources.',
  });

  const data = new DataStack(app, stackId(config, 'data'), {
    env: config.env,
    foundation: config,
    vpc: network.vpc,
    databaseSecurityGroup: network.databaseSecurityGroup,
    description: 'Boundary stack for storage and data resources.',
  });

  const services = new ServicesStack(app, stackId(config, 'services'), {
    env: config.env,
    foundation: config,
    description: 'Boundary stack for runtime services.',
  });

  const gatewayService = new GatewayServiceStack(app, stackId(config, 'gateway-service'), {
    env: config.env,
    foundation: config,
    vpc: network.vpc,
    profileServiceBaseUrl: 'http://profile-service:8080',
    description: 'Gateway service stack for the public API.',
  });

  data.addDependency(network);
  services.addDependency(data);
  gatewayService.addDependency(network);
  gatewayService.addDependency(services);

  let observability: ObservabilityStack | undefined;
  if (options.enableObservability) {
    observability = new ObservabilityStack(app, stackId(config, 'observability'), {
      env: config.env,
      foundation: config,
      description: 'Optional boundary stack for observability resources.',
    });
    observability.addDependency(services);
  }

  return { network, data, services, gatewayService, observability, config };
}


export function deployFoundationFromContext(app: App) {
  const stage = app.node.tryGetContext('stage') as string | undefined;
  const appName = app.node.tryGetContext('appName') as string | undefined;
  const enableObservabilityContext = app.node.tryGetContext('enableObservability');
  const enableObservability =
    enableObservabilityContext === true ||
    enableObservabilityContext === 'true' ||
    process.env.CDK_ENABLE_OBSERVABILITY === 'true';

  return deployFoundation(app, { stage, appName, enableObservability });
}