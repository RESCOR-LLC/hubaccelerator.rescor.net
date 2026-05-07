"""Shared pytest fixtures for the HubAccelerator test suite."""

from __future__ import annotations

from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Sample finding fixtures — used across unit and integration tests.
# Each fixture returns a *fresh* dict per call so tests can mutate without
# bleeding state.
# ---------------------------------------------------------------------------


@pytest.fixture
def aws_native_finding() -> dict[str, Any]:
    """A minimal Security Hub finding originating from a native AWS source
    (GuardDuty in this example). Use this as the baseline for tests that
    don't need provenance variation."""

    return {
        "SchemaVersion": "2018-10-08",
        "Id": "arn:aws:guardduty:us-east-1:111122223333:detector/abc/finding/test-1",
        "ProductArn": "arn:aws:securityhub:us-east-1::product/aws/guardduty",
        "ProductName": "GuardDuty",
        "CompanyName": "AWS",
        "Region": "us-east-1",
        "GeneratorId": "guardduty/UnauthorizedAccess",
        "AwsAccountId": "111122223333",
        "Types": ["TTPs/Initial Access/UnauthorizedAccess"],
        "CreatedAt": "2026-01-15T12:00:00.000Z",
        "UpdatedAt": "2026-01-15T12:00:00.000Z",
        "Severity": {"Label": "HIGH", "Normalized": 70, "Original": "7.0"},
        "Title": "Test finding (AWS native)",
        "Description": "This is a test finding for unit-test fixtures.",
        "Resources": [
            {
                "Type": "AwsEc2Instance",
                "Id": "arn:aws:ec2:us-east-1:111122223333:instance/i-0123456789abcdef0",
                "Region": "us-east-1",
            }
        ],
        "Workflow": {"Status": "NEW"},
        "RecordState": "ACTIVE",
        "FindingProviderFields": {
            "Severity": {"Label": "HIGH", "Original": "7.0"},
            "Types": ["TTPs/Initial Access/UnauthorizedAccess"],
        },
    }


@pytest.fixture
def azure_via_wiz_finding() -> dict[str, Any]:
    """A Security Hub finding whose underlying resource is in Azure but is
    aggregated via a third-party integration (Wiz, in this example).
    The HubAccelerator code path must handle non-AWS-native findings
    without choking on AWS-shaped Resource fields it does not have."""

    return {
        "SchemaVersion": "2018-10-08",
        "Id": "wiz-finding/azure-vm/test-1",
        "ProductArn": "arn:aws:securityhub:us-east-1:111122223333:product/wiz/wiz",
        "ProductName": "Wiz",
        "CompanyName": "Wiz",
        "Region": "us-east-1",
        "GeneratorId": "wiz/azure-vm-misconfiguration",
        "AwsAccountId": "111122223333",
        "Types": ["Software and Configuration Checks/Vulnerabilities/CVE"],
        "CreatedAt": "2026-01-15T12:00:00.000Z",
        "UpdatedAt": "2026-01-15T12:00:00.000Z",
        "Severity": {"Label": "MEDIUM", "Normalized": 40},
        "Title": "Test finding (Azure VM via Wiz)",
        "Description": "Azure-resident VM finding aggregated via Wiz integration.",
        "Resources": [
            {
                # Non-AWS resource — Wiz uses the "Other" type to express
                # cross-cloud findings.
                "Type": "Other",
                "Id": "azure://subscriptions/abc/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-test",
                "Region": "eastus",
                "Details": {
                    "Other": {
                        "cloud": "azure",
                        "vmId": "vm-test",
                    }
                },
            }
        ],
        "Workflow": {"Status": "NEW"},
        "RecordState": "ACTIVE",
    }


@pytest.fixture
def gcp_via_prisma_finding() -> dict[str, Any]:
    """Same idea as the Azure fixture but Google Cloud aggregated via
    Prisma Cloud."""

    return {
        "SchemaVersion": "2018-10-08",
        "Id": "prisma-finding/gcp-bucket/test-1",
        "ProductArn": "arn:aws:securityhub:us-east-1:111122223333:product/palo-alto-networks/prisma-cloud",
        "ProductName": "Prisma Cloud",
        "CompanyName": "Palo Alto Networks",
        "Region": "us-east-1",
        "GeneratorId": "prisma/gcp-storage-public",
        "AwsAccountId": "111122223333",
        "Types": ["Software and Configuration Checks/Industry and Regulatory Standards"],
        "CreatedAt": "2026-01-15T12:00:00.000Z",
        "UpdatedAt": "2026-01-15T12:00:00.000Z",
        "Severity": {"Label": "HIGH", "Normalized": 70},
        "Title": "Test finding (GCP storage via Prisma Cloud)",
        "Description": "GCP storage bucket finding via Prisma Cloud integration.",
        "Resources": [
            {
                "Type": "Other",
                "Id": "gcp://projects/test-project/buckets/public-bucket",
                "Region": "us-central1",
                "Details": {
                    "Other": {
                        "cloud": "gcp",
                        "project": "test-project",
                    }
                },
            }
        ],
        "Workflow": {"Status": "NEW"},
        "RecordState": "ACTIVE",
    }


# ---------------------------------------------------------------------------
# AWS env fixtures — moto uses these to set up its mocks.
# ---------------------------------------------------------------------------


@pytest.fixture
def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set fake AWS credentials so boto3 does not pick up real ones during
    tests. Required by moto."""

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear HubAccelerator-related env vars so tests get deterministic
    behaviour regardless of the developer's shell."""

    for var in (
        "HUBACCELERATOR_REGIONLIST",
        "HUBACCELERATOR_BUCKET",
        "HUBACCELERATOR_REGION",
        "CSV_SECURITYHUB_REGIONLIST",
        "CSV_PRIMARY_REGION",
        "CSV_SECURITYHUB_BUCKET",
    ):
        monkeypatch.delenv(var, raising=False)
