import { App } from 'aws-cdk-lib';
import { Match, Template } from 'aws-cdk-lib/assertions';

import { DataStack } from '../../lib/stacks/data-stack';
import { NetworkStack } from '../../lib/stacks/network-stack';

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

	const stack = new DataStack(app, 'cv-match-dev-data', {
		env,
		foundation: {
			appName: 'cv-match',
			stage: 'dev',
			env,
		},
		vpc: network.vpc,
		databaseSecurityGroup: network.databaseSecurityGroup,
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