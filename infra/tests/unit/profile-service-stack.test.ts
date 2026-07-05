import { App } from 'aws-cdk-lib';
import { Match, Template } from 'aws-cdk-lib/assertions';

import { NetworkStack } from '../../cdk/lib/stacks/base/network';
import { SecurityStack } from '../../cdk/lib/stacks/base/security';
import { ComputeStack } from '../../cdk/lib/stacks/shared/compute';
import { DataStack } from '../../cdk/lib/stacks/shared/data';
import { ProfileServiceStack } from '../../cdk/lib/stacks/services/profile';

test('profile service stack creates an internal ecs service backed by the shared data plane', () => {
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

	const data = new DataStack(app, 'cv-match-dev-data', {
		env,
		foundation: {
			appName: 'cv-match',
			stage: 'dev',
			env,
		},
		vpc: network.vpc,
		databaseSecurityGroup: security.databaseSecurityGroup,
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

	const stack = new ProfileServiceStack(app, 'cv-match-dev-profile', {
		env,
		foundation: {
			appName: 'cv-match',
			stage: 'dev',
			env,
		},
		vpc: network.vpc,
		cluster: compute.cluster,
		securityGroups: [security.serviceSecurityGroup],
		databaseSecret: data.database.secret!,
		databaseHost: data.database.instanceEndpoint.hostname,
		cvBucket: data.cvBucket,
	});

	const template = Template.fromStack(stack);

	template.resourceCountIs('AWS::ECS::Service', 1);
	template.resourceCountIs('AWS::ElasticLoadBalancingV2::LoadBalancer', 0);
	template.hasResourceProperties('AWS::ECS::Service', {
		ServiceConnectConfiguration: Match.anyValue(),
	});
	template.hasOutput('ProfileServiceUrl', {
		Value: 'http://profile-service:8080',
	});
});