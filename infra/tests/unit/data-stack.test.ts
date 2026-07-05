import { App } from 'aws-cdk-lib';
import { Match, Template } from 'aws-cdk-lib/assertions';

import { NetworkStack } from '../../cdk/lib/stacks/base/network';
import { SecurityStack } from '../../cdk/lib/stacks/base/security';
import { DataStack } from '../../cdk/lib/stacks/shared/data';

test('data stack creates a cheap postgres instance and private cv bucket', () => {
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

	const security = new SecurityStack(app, 'cv-match-dev-security', {
		env,
		foundation: {
			appName: 'cv-match',
			stage: 'dev',
			env,
		},
		vpc: network.vpc,
	});

	const stack = new DataStack(app, 'cv-match-dev-data', {
		env,
		foundation: {
			appName: 'cv-match',
			stage: 'dev',
			env,
		},
		vpc: network.vpc,
		databaseSecurityGroup: security.databaseSecurityGroup,
	});

	const template = Template.fromStack(stack);

	template.resourceCountIs('AWS::RDS::DBInstance', 1);
	template.resourceCountIs('AWS::S3::Bucket', 1);
	template.hasOutput('DatabaseEndpointAddress', {
		Value: Match.anyValue(),
	});
	template.hasOutput('CvBucketName', {
		Value: Match.anyValue(),
	});
});

test('data stack supports self-managed database security group fallback', () => {
	const app = new App();
	const env = { account: '111111111111', region: 'us-east-1' };

	const network = new NetworkStack(app, 'cv-match-dev-network-fallback', {
		env,
		foundation: {
			appName: 'cv-match',
			stage: 'dev',
			env,
		},
	});

	const stack = new DataStack(app, 'cv-match-dev-data-fallback', {
		env,
		foundation: {
			appName: 'cv-match',
			stage: 'dev',
			env,
		},
		vpc: network.vpc,
		allowSelfManagedSecurityGroup: true,
	});

	const template = Template.fromStack(stack);

	template.resourceCountIs('AWS::EC2::SecurityGroup', 1);
	template.resourceCountIs('AWS::RDS::DBInstance', 1);
});