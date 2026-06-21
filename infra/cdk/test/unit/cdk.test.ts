import { App } from 'aws-cdk-lib';

import { deployFoundation } from '../../bin/foundation';

const env = { account: '111111111111', region: 'us-east-1' };

test('creates required foundation boundaries', () => {
	const app = new App();
	deployFoundation(app, { appName: 'cv-match', stage: 'dev', env });
	const assembly = app.synth();

	const stackNames = assembly.stacks.map((stack) => stack.stackName);

	expect(stackNames).toEqual(
		expect.arrayContaining([
			'cv-match-dev-network',
			'cv-match-dev-data',
			'cv-match-dev-services',
			'cv-match-dev-gateway-service',
		]),
	);
	expect(stackNames).not.toContain('cv-match-dev-observability');
});

test('creates optional observability boundary when enabled', () => {
	const app = new App();
	deployFoundation(app, {
		appName: 'cv-match',
		stage: 'dev',
		env,
		enableObservability: true,
	});
	const assembly = app.synth();

	const stackNames = assembly.stacks.map((stack) => stack.stackName);
	expect(stackNames).toContain('cv-match-dev-observability');
});