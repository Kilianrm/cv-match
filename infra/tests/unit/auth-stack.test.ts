import { App } from 'aws-cdk-lib';
import { Match, Template } from 'aws-cdk-lib/assertions';

import { AuthStack } from '../../cdk/lib/stacks/shared/auth';

test('auth stack creates cognito resources and exposes oauth outputs', () => {
	const app = new App();
	const env = { account: '111111111111', region: 'us-east-1' };

	const stack = new AuthStack(app, 'cv-match-dev-auth', {
		env,
		foundation: {
			appName: 'cv-match',
			stage: 'dev',
			env,
		},
		localFrontendBaseUrl: 'http://localhost:3000',
	});

	const template = Template.fromStack(stack);

	template.resourceCountIs('AWS::Cognito::UserPool', 1);
	template.resourceCountIs('AWS::Cognito::UserPoolClient', 1);
	template.resourceCountIs('AWS::Cognito::UserPoolDomain', 1);
	template.hasOutput('CognitoAuthorizationEndpoint', {
		Value: Match.anyValue(),
	});
	template.hasOutput('CognitoJwksUrl', {
		Value: Match.anyValue(),
	});
});
