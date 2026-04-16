/**
 * HubAcceleratorStack — CDK stack for the HubAccelerator infrastructure.
 *
 * Replaces three CloudFormation templates (CsvDatastore, CsvExporter, CsvUpdater)
 * with a single CDK stack.
 *
 * Creates:
 *   - S3 bucket with object lock, encryption, lifecycle policies
 *   - SSM parameters for configuration (/csvManager/*)
 *   - IAM role for Lambda execution (SecurityHub, S3, SSM, STS)
 *   - Lambda function for scheduled exports (csvExporter)
 *   - Lambda function for bulk updates (csvUpdater)
 *   - EventBridge rule for scheduled exports
 *
 * Outputs:
 *   - BucketName, ExporterFunctionName, UpdaterFunctionName, RoleArn
 */

const { Stack, Duration, RemovalPolicy, CfnOutput } = require('aws-cdk-lib');
const s3 = require('aws-cdk-lib/aws-s3');
const lambda = require('aws-cdk-lib/aws-lambda');
const events = require('aws-cdk-lib/aws-events');
const targets = require('aws-cdk-lib/aws-events-targets');
const iam = require('aws-cdk-lib/aws-iam');
const ssm = require('aws-cdk-lib/aws-ssm');

class HubAcceleratorStack extends Stack {
  constructor(scope, id, props) {
    super(scope, id, props);

    const codeFolder = props?.codeFolder || 'Code';
    const findingsFolder = props?.findingsFolder || 'Findings';
    const exportSchedule = props?.exportSchedule || 'cron(0 8 ? * SUN *)';
    const exportFilter = props?.exportFilter || 'HighActive';
    const retentionDays = props?.retentionDays || 365;
    const glacierDays = props?.glacierDays || 90;
    const regions = props?.regions || '';

    // ── S3 Bucket ─────────────────────────────────────────────────────
    const bucket = new s3.Bucket(this, 'FindingsBucket', {
      bucketName: `hubaccelerator-${this.account}-${this.region}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true,
      objectLockEnabled: true,
      removalPolicy: RemovalPolicy.RETAIN,
      lifecycleRules: [
        {
          id: 'GlacierTransition',
          prefix: `${findingsFolder}/`,
          transitions: [
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: Duration.days(glacierDays),
            },
          ],
          expiration: Duration.days(retentionDays),
          noncurrentVersionExpiration: Duration.days(retentionDays),
        },
      ],
    });

    // ── SSM Parameters ────────────────────────────────────────────────
    new ssm.StringParameter(this, 'ParamBucket', {
      parameterName: '/csvManager/bucket',
      stringValue: bucket.bucketName,
      description: 'HubAccelerator S3 bucket name',
    });

    new ssm.StringParameter(this, 'ParamCodeFolder', {
      parameterName: '/csvManager/folder/code',
      stringValue: codeFolder,
      description: 'S3 prefix for Lambda code archives',
    });

    new ssm.StringParameter(this, 'ParamFindingsFolder', {
      parameterName: '/csvManager/folder/findings',
      stringValue: findingsFolder,
      description: 'S3 prefix for exported finding CSVs',
    });

    new ssm.StringParameter(this, 'ParamPartition', {
      parameterName: '/csvManager/partition',
      stringValue: this.partition,
      description: 'AWS partition (aws or aws-us-gov)',
    });

    if (regions) {
      new ssm.StringParameter(this, 'ParamRegionList', {
        parameterName: '/csvManager/regionList',
        stringValue: regions,
        description: 'Comma-separated list of regions to scan',
      });
    }

    // ── IAM Role ──────────────────────────────────────────────────────
    const role = new iam.Role(this, 'HubAcceleratorRole', {
      roleName: 'HubAcceleratorRole',
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal('lambda.amazonaws.com'),
        new iam.ServicePrincipal('ssm.amazonaws.com'),
      ),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    // SecurityHub read + write
    role.addToPolicy(new iam.PolicyStatement({
      sid: 'SecurityHubAccess',
      effect: iam.Effect.ALLOW,
      actions: [
        'securityhub:GetFindings',
        'securityhub:BatchUpdateFindings',
        'securityhub:DescribeHub',
      ],
      resources: ['*'],
    }));

    // S3 bucket access
    bucket.grantReadWrite(role);

    // SSM parameter access
    role.addToPolicy(new iam.PolicyStatement({
      sid: 'SsmAccess',
      effect: iam.Effect.ALLOW,
      actions: [
        'ssm:GetParameter',
        'ssm:GetParameters',
        'ssm:PutParameter',
      ],
      resources: [
        `arn:${this.partition}:ssm:${this.region}:${this.account}:parameter/csvManager/*`,
      ],
    }));

    // STS for cross-account assume role
    role.addToPolicy(new iam.PolicyStatement({
      sid: 'StsAccess',
      effect: iam.Effect.ALLOW,
      actions: ['sts:AssumeRole', 'sts:GetCallerIdentity'],
      resources: ['*'],
    }));

    // EC2 describe regions (for region enumeration)
    role.addToPolicy(new iam.PolicyStatement({
      sid: 'Ec2DescribeRegions',
      effect: iam.Effect.ALLOW,
      actions: ['ec2:DescribeRegions'],
      resources: ['*'],
    }));

    // ── Lambda: Exporter ──────────────────────────────────────────────
    const exporterFn = new lambda.Function(this, 'Exporter', {
      functionName: 'HubAccelerator-Exporter',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'hubaccelerator.exporter.lambdaHandler',
      code: lambda.Code.fromAsset('../src'),
      role,
      timeout: Duration.minutes(15),
      memorySize: 512,
      environment: {
        HUBACCELERATOR_REGION: this.region,
      },
    });

    // ── Lambda: Updater ───────────────────────────────────────────────
    const updaterFn = new lambda.Function(this, 'Updater', {
      functionName: 'HubAccelerator-Updater',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'hubaccelerator.updater.lambdaHandler',
      code: lambda.Code.fromAsset('../src'),
      role,
      timeout: Duration.minutes(15),
      memorySize: 512,
      environment: {
        HUBACCELERATOR_REGION: this.region,
      },
    });

    // ── EventBridge: Scheduled Export ──────────────────────────────────
    const rule = new events.Rule(this, 'ExportSchedule', {
      ruleName: 'HubAccelerator-ExportSchedule',
      schedule: events.Schedule.expression(exportSchedule),
    });

    rule.addTarget(new targets.LambdaFunction(exporterFn, {
      event: events.RuleTargetInput.fromObject({
        filters: exportFilter,
        bucket: bucket.bucketName,
        region: this.region,
      }),
    }));

    // ── Outputs ───────────────────────────────────────────────────────
    new CfnOutput(this, 'BucketName', {
      value: bucket.bucketName,
      description: 'S3 bucket for findings',
    });

    new CfnOutput(this, 'ExporterFunction', {
      value: exporterFn.functionName,
      description: 'Lambda function for scheduled exports',
    });

    new CfnOutput(this, 'UpdaterFunction', {
      value: updaterFn.functionName,
      description: 'Lambda function for bulk updates',
    });

    new CfnOutput(this, 'RoleArn', {
      value: role.roleArn,
      description: 'IAM role ARN for CLI usage',
    });
  }
}

module.exports = { HubAcceleratorStack };
