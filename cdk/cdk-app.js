#!/usr/bin/env node
const { App } = require('aws-cdk-lib');
const { HubAcceleratorStack } = require('./hubaccelerator-stack');

const app = new App();

new HubAcceleratorStack(app, 'HubAcceleratorStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },

  // Override via CDK context:
  //   cdk deploy --context exportSchedule="cron(0 6 ? * MON-FRI *)"
  exportSchedule: app.node.tryGetContext('exportSchedule') || 'cron(0 8 ? * SUN *)',
  exportFilter: app.node.tryGetContext('exportFilter') || 'HighActive',
  retentionDays: parseInt(app.node.tryGetContext('retentionDays') || '365'),
  glacierDays: parseInt(app.node.tryGetContext('glacierDays') || '90'),
  regions: app.node.tryGetContext('regions') || '',
});
