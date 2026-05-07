# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability in HubAccelerator, please report it privately rather than filing a public GitHub issue. Public disclosure of an unpatched vulnerability puts other users at risk.

**Email:** office@rescor.net with the subject line `[HubAccelerator security]`.

Include:

- A description of the vulnerability and the impact you understand it to have.
- Steps to reproduce, or a proof-of-concept that demonstrates the issue.
- The version (commit hash or release tag) you tested against.
- Whether you intend to disclose publicly, and on what timeline.

You can expect:

- An acknowledgement within 5 business days of receipt.
- A first-pass triage and a likely fix timeline within 10 business days, or an explanation if it will take longer.
- Credit in the release notes when the fix lands, unless you ask to remain anonymous.

## Scope

HubAccelerator is a Python package plus AWS infrastructure-as-code (CDK and CloudFormation). The following are in scope:

- The `hubaccelerator-export` and `hubaccelerator-update` command-line tools and the underlying `hubaccelerator` Python package (`src/hubaccelerator/`).
- The CDK stack in `cdk/` and the CloudFormation templates in `cfn/`.
- IAM roles, S3 bucket policies, and Lambda function configurations produced by the deployment.

Out of scope:

- Vulnerabilities in upstream dependencies (boto3, AWS CDK, AWS SDK). Please report those to their respective maintainers; HubAccelerator will pin or upgrade as needed once an upstream fix is available.
- Vulnerabilities in AWS Security Hub itself. Report those to AWS Security via <https://aws.amazon.com/security/vulnerability-reporting/>.
- Misconfigurations in your own AWS environment that are not introduced by the HubAccelerator deployment.

## Threat model

HubAccelerator is intended to run with **read-only Security Hub credentials** for the exporter and **scoped write credentials** (`securityhub:BatchUpdateFindings` only) for the updater. It assumes:

- The S3 bucket holding exported findings is private, encrypted at rest, and access-logged.
- The IAM role used for cross-account access enforces a specific trust policy and external ID.
- The CSV file produced by the exporter is treated as containing sensitive information until disposed of.

If your deployment relaxes these assumptions, the security guarantees relax with them. The CDK stack provides defaults aligned with the intended threat model; the CloudFormation templates are kept for reference but should be reviewed before use.

## Coordinated disclosure

We follow industry-standard coordinated disclosure. We will work with you on a disclosure timeline that gives users time to update before details are public. The default is 90 days from initial report; we may negotiate shorter or longer depending on severity and patch complexity.
