module.exports = {
  testEnvironment: 'node',
  roots: ['<rootDir>/../tests/unit'],
  modulePaths: ['<rootDir>/node_modules'],
  testMatch: ['**/*.test.ts'],
  transform: {
    '^.+\\.tsx?$': 'ts-jest'
  },
  setupFilesAfterEnv: ['aws-cdk-lib/testhelpers/jest-autoclean'],
};
