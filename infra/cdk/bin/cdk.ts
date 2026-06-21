#!/usr/bin/env node
import { App } from 'aws-cdk-lib';
import { deployFoundationFromContext } from './foundation';

const app = new App();
deployFoundationFromContext(app);
