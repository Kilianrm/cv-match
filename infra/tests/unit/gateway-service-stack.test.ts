import { App } from 'aws-cdk-lib';
import { Match, Template } from 'aws-cdk-lib/assertions';

import { NetworkStack } from '../../cdk/lib/stacks/base/network';
import { ComputeStack } from '../../cdk/lib/stacks/shared/compute';
import { GatewayServiceStack } from '../../cdk/lib/stacks/services/gateway';

test('gateway service stack is compatible with the network stack vpc', () => {
	const app = new App();
	const env = { account: '111111111111', region: 'us-east-1' };

	const network = new NetworkStack(app, 'cv-match-dev-network', {
		env,
		foundation: {
			appName: 'cv-match',
			stage: 'dev',
			env,
		},
	});

	const compute = new ComputeStack(app, 'cv-match-dev-compute', {
		env,
		foundation: {
			appName: 'cv-match',
			stage: 'dev',
			env,
		},
		vpc: network.vpc,
	});

	const stack = new GatewayServiceStack(app, 'cv-match-dev-gateway', {
		env,
		foundation: {
			appName: 'cv-match',
			stage: 'dev',
			env,
		},
		vpc: network.vpc,
		cluster: compute.cluster,
		profileServiceBaseUrl: 'http://profile-service:8080',
	});

	const template = Template.fromStack(stack);

	template.resourceCountIs('AWS::ECS::Service', 1);
	template.resourceCountIs('AWS::ElasticLoadBalancingV2::LoadBalancer', 1);
	template.resourceCountIs('AWS::EC2::VPC', 0);
	template.hasResourceProperties('AWS::ECS::Service', {
		ServiceConnectConfiguration: Match.anyValue(),
	});
	template.hasOutput('GatewayServiceUrl', {
		Description: 'Public URL for the gateway-service ALB in this environment.',
	});
});