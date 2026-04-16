# HubAccelerator

**The Security Hub Backlog Accelerator**

HubAccelerator exports AWS Security Hub findings to CSV and allows bulk updates by editing the CSV — converting a per-finding console workflow into a spreadsheet-driven bulk operation.

## The Problem

AWS Security Hub aggregates findings from GuardDuty, Inspector, Macie, Config, and third-party tools. Organizations with even modest AWS environments accumulate thousands to millions of findings. The Security Hub console allows updating findings one at a time. Automation Rules (introduced 2023) handle pattern-based suppression, but periodic manual review of large finding sets — annotating, accepting, suppressing, or escalating — still requires a bulk workflow that the console does not provide.

## What HubAccelerator Does

**HubAccelerator Exporter (`csvExporter.py`)** exports Security Hub findings to a CSV file stored in S3. It can run as:
- A CLI command from your workstation
- An AWS Lambda function on a schedule (via EventBridge)
- An SSM Automation for on-demand execution

**HubAccelerator Updater (`csvUpdater.py`)** reads a modified CSV and pushes changes back to Security Hub via the `BatchUpdateFindings` API. Updatable fields include:
- **Workflow status** — NEW, NOTIFIED, SUPPRESSED, RESOLVED
- **Severity** — override the scanner's severity with your own assessment
- **Confidence** — your confidence in the finding's accuracy
- **Criticality** — business criticality of the affected resource
- **Note** — free-text annotation explaining your disposition
- **User-defined fields** — custom key-value pairs for organizational tracking

**HubAccelerator Prepare (`csvPrepare.py`)** packages the Lambda deployment artifact and uploads it to S3.

## Architecture

```
[EventBridge Schedule] → [Lambda: csvExporter] → [S3: findings.csv]
                                                        ↓
                                                  [Download CSV]
                                                        ↓
                                                  [Edit in Excel]
                                                        ↓
                                                  [Upload CSV]
                                                        ↓
                              [CLI: csvUpdater] → [Security Hub BatchUpdateFindings]
```

### Local File Support

Both the exporter and updater support local file operations as an alternative to S3. The exporter can write findings directly to a local CSV file (use `--retain-local` to keep it), and the updater can read from either an S3 URL (`s3://bucket/key`) or a local file path. This is often the most direct workflow for analysts working from their workstation:

```bash
# Export to S3 and keep a local copy
python3 src/csvExporter.py --role-arn ... --primary-region us-east-1 \
  --bucket my-bucket --retain-local

# Edit the local CSV in Excel, then update directly from the local file
python3 src/csvUpdater.py --role-arn ... --primary-region us-east-1 \
  --input /tmp/findings-2026-04-16.csv
```

## Requirements

- Python 3.12+ (Lambda runtime; CLI works with 3.9+)
- AWS credentials with Security Hub read access (exporter) and write access (updater)
- An S3 bucket for storing exported findings
- An IAM role for Lambda execution (if using scheduled exports)
- GovCloud compatible (aws and aws-us-gov partitions supported)

## Installation

### Infrastructure (CDK)

A single CDK stack in `cdk/` provisions all required AWS resources:

```bash
cd cdk
npm install
cdk deploy
```

This creates: S3 bucket (encrypted, versioned, object lock, lifecycle policies), SSM parameters, IAM role, Lambda functions (exporter + updater), and an EventBridge schedule for automated exports.

Override defaults via CDK context:
```bash
cdk deploy --context exportSchedule="cron(0 6 ? * MON-FRI *)" \
           --context regions="us-east-1,us-west-2"
```

Legacy CloudFormation templates are retained in `cfn/` for reference.

### CLI Usage

```bash
# Export findings
python3 src/csvExporter.py \
  --role-arn arn:aws:iam::ACCOUNT:role/HubAcceleratorRole \
  --primary-region us-east-1 \
  --bucket your-findings-bucket \
  --filters HighActive

# Update findings from modified CSV
python3 src/csvUpdater.py \
  --role-arn arn:aws:iam::ACCOUNT:role/HubAcceleratorRole \
  --primary-region us-east-1 \
  --input s3://your-findings-bucket/Findings/latest.csv
```

## Project Structure

```
hubaccelerator.rescor.net/
├── README.md
├── src/
│   ├── csvExporter.py      — Export findings to CSV (CLI + Lambda)
│   ├── csvUpdater.py       — Bulk update findings from CSV (CLI + Lambda)
│   ├── csvPrepare.py       — Package Lambda deployment artifact
│   └── csvObjects.py       — Shared AWS service abstractions
├── cfn/
│   ├── CsvDatastore.yaml   — S3 bucket + lifecycle policies
│   ├── CsvExporter.yaml    — Export Lambda + EventBridge + SSM
│   └── CsvUpdater.yaml     — Update Lambda + SSM
├── docs/
│   ├── HubAccelerator-UserGuide.docx
│   ├── HubAccelerator-Overview.pptx
│   └── HubAccelerator-README-legacy.pdf
├── archive/                — Applied patches (historical)
└── scripts/                — Utility scripts
```

## Configuration

HubAccelerator reads configuration from AWS Systems Manager Parameter Store under the `/csvManager/` prefix:

| Parameter | Description |
|-----------|-------------|
| `/csvManager/regionList` | Comma-separated list of regions to scan |
| `/csvManager/bucket` | S3 bucket name for findings |
| `/csvManager/folder/findings` | S3 prefix for exported CSV files |

Environment variables override SSM parameters:
- `CSV_SECURITYHUB_REGIONLIST` — region list override
- `CSV_SECURITYHUB_BUCKET` — bucket override

## Relationship to AWS Security Hub Native Features

Security Hub's [Automation Rules](https://docs.aws.amazon.com/securityhub/latest/userguide/automation-rules.html) (2023) cover pattern-based auto-suppression — "whenever finding X matches criteria Y, suppress it." This handles the "suppress this forever" use case.

HubAccelerator complements Automation Rules for the use case they don't cover: **periodic manual review of large finding sets**. When an analyst needs to review 500 findings, make disposition decisions in a spreadsheet, and push those decisions back to Security Hub in bulk, HubAccelerator provides the workflow.

## License

Copyright 2020–2026 Andrew T. Robinson / RESCOR LLC. All Rights Reserved.

## Author

Andrew T. Robinson — [RESCOR LLC](https://www.rescor.net)
