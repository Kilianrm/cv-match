import { App } from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';

import { NetworkStack } from '../../lib/stacks/network-stack';
import { GatewayServiceStack } from '../../lib/stacks/services/gateway-service-stack';

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

	const stack = new GatewayServiceStack(app, 'cv-match-dev-gateway-service', {
		env,
		foundation: {
			appName: 'cv-match',
			stage: 'dev',
			env,
		},
		vpc: network.vpc,
		profileServiceBaseUrl: 'http://profile-service:8080',
	});

	const template = Template.fromStack(stack);

	template.resourceCountIs('AWS::ECS::Service', 1);
	template.resourceCountIs('AWS::ElasticLoadBalancingV2::LoadBalancer', 1);
	template.resourceCountIs('AWS::EC2::VPC', 0);
	template.hasOutput('GatewayServiceUrl', {
		Description: 'Public URL for the gateway-service ALB in this environment.',
	});
});