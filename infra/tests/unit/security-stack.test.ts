import { App } from 'aws-cdk-lib';
import { Match, Template } from 'aws-cdk-lib/assertions';

import { NetworkStack } from '../../cdk/lib/stacks/base/network';
import { SecurityStack } from '../../cdk/lib/stacks/base/security';

test('security stack creates service and database security groups', () => {
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

	const stack = new SecurityStack(app, 'cv-match-dev-security', {
		env,
		foundation: {
			appName: 'cv-match',
			stage: 'dev',
			env,
		},
		vpc: network.vpc,
	});

	const template = Template.fromStack(stack);

	template.resourceCountIs('AWS::EC2::SecurityGroup', 2);
	template.hasOutput('ServiceSecurityGroupId', {
		Value: Match.anyValue(),
	});
	template.hasOutput('DatabaseSecurityGroupId', {
		Value: Match.anyValue(),
	});
});