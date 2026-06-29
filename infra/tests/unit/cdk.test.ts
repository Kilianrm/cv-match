import { App } from 'aws-cdk-lib';

import { deployFoundation } from '../../cdk/bin/foundation';

const env = { account: '111111111111', region: 'us-east-1' };

test('creates required foundation boundaries', () => {
	const app = new App();
	deployFoundation(app, { appName: 'cv-match', stage: 'dev', env });
	const assembly = app.synth();

	const stackNames = assembly.stacks.map((stack) => stack.stackName);

	expect(stackNames).toEqual(
		expect.arrayContaining([
			'cv-match-dev-network',
			'cv-match-dev-security',
			'cv-match-dev-data',
			'cv-match-dev-auth',
			'cv-match-dev-gateway',
			'cv-match-dev-profile',
		]),
	);
});

test('supports foundation deployment without shared security stack', () => {
	const app = new App();
	deployFoundation(app, { appName: 'cv-match', stage: 'dev', env, useSharedSecurity: false });
	const assembly = app.synth();

	const stackNames = assembly.stacks.map((stack) => stack.stackName);

	expect(stackNames).toEqual(
		expect.arrayContaining([
			'cv-match-dev-network',
			'cv-match-dev-data',
			'cv-match-dev-auth',
			'cv-match-dev-profile',
			'cv-match-dev-gateway',
		]),
	);
	expect(stackNames).not.toContain('cv-match-dev-security');
});