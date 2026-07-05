import { App } from 'aws-cdk-lib';
import { Match, Template } from 'aws-cdk-lib/assertions';

import { NetworkStack } from '../../cdk/lib/stacks/base/network';

test('network stack creates the vpc and subnet baseline', () => {
	const app = new App();
	const env = { account: '111111111111', region: 'us-east-1' };

	const stack = new NetworkStack(app, 'cv-match-dev-network', {
		env,
		foundation: {
			appName: 'cv-match',
			stage: 'dev',
			env,
		},
	});

	const template = Template.fromStack(stack);

	template.resourceCountIs('AWS::EC2::VPC', 1);
	template.resourceCountIs('AWS::EC2::InternetGateway', 1);
	template.resourceCountIs('AWS::EC2::NatGateway', 0);
	template.resourceCountIs('AWS::EC2::Subnet', 6);
	template.resourceCountIs('AWS::EC2::SecurityGroup', 1);
	template.hasOutput('VpcId', {
		Value: Match.anyValue(),
	});
});