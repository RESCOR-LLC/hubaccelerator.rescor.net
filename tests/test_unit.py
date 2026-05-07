"""Unit tests for pure-function and object behaviour — no AWS APIs touched."""

from __future__ import annotations

import pytest

from hubaccelerator.exporter import getFilters
from hubaccelerator.objects import error_code, env
from hubaccelerator.updater import InputDiscriminator


# ---------------------------------------------------------------------------
# getFilters — translates filter input (None, dict, JSON string, or the
# canned "HighActive" sentinel) into the dict shape Security Hub expects.
# ---------------------------------------------------------------------------


class TestGetFilters:
    def test_none_returns_empty_dict(self) -> None:
        assert getFilters(None) == {}

    def test_empty_string_returns_empty_dict(self) -> None:
        assert getFilters("") == {}

    def test_dict_passes_through(self) -> None:
        candidate = {"SeverityLabel": [{"Value": "HIGH", "Comparison": "EQUALS"}]}
        assert getFilters(candidate) == candidate

    def test_high_active_sentinel(self) -> None:
        result = getFilters("HighActive")
        assert "SeverityLabel" in result
        assert "RecordState" in result
        labels = {entry["Value"] for entry in result["SeverityLabel"]}
        assert labels == {"CRITICAL", "HIGH"}

    def test_json_string_parses(self) -> None:
        result = getFilters('{"RecordState":[{"Comparison":"EQUALS","Value":"ACTIVE"}]}')
        assert result == {"RecordState": [{"Comparison": "EQUALS", "Value": "ACTIVE"}]}

    def test_malformed_json_returns_empty_dict(self) -> None:
        # Should log an error but not raise.
        assert getFilters("{this is not json}") == {}


# ---------------------------------------------------------------------------
# InputDiscriminator — distinguishes s3:// URLs from local paths.
# ---------------------------------------------------------------------------


class TestInputDiscriminator:
    def test_s3_url_parsed(self) -> None:
        d = InputDiscriminator("s3://my-bucket/path/to/findings.csv")
        assert d.isLocal is False
        assert d.bucket == "my-bucket"
        assert d.key == "path/to/findings.csv"
        assert d.path is None

    def test_s3_url_case_insensitive_scheme(self) -> None:
        d = InputDiscriminator("S3://my-bucket/findings.csv")
        assert d.isLocal is False
        assert d.bucket == "my-bucket"

    def test_local_path_classified_as_local(self) -> None:
        d = InputDiscriminator("/tmp/findings.csv")
        assert d.isLocal is True
        assert d.path == "/tmp/findings.csv"
        assert d.bucket is None
        assert d.key is None

    def test_relative_local_path(self) -> None:
        d = InputDiscriminator("./output/findings.csv")
        assert d.isLocal is True
        assert d.path == "./output/findings.csv"

    def test_no_key_in_s3_url(self) -> None:
        # s3://bucket-only/ (or even s3://bucket — pathological but should not crash)
        d = InputDiscriminator("s3://bucket-only/")
        assert d.isLocal is False
        assert d.bucket == "bucket-only"
        assert d.key == ""


# ---------------------------------------------------------------------------
# env() — env-var lookup with deprecation-aware fallback.
# ---------------------------------------------------------------------------


class TestEnv:
    def test_returns_default_when_unset(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        assert env("HUBACCELERATOR_BUCKET", default="fallback") == "fallback"

    def test_returns_value_when_set(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HUBACCELERATOR_BUCKET", "bucket-from-new-name")
        assert env("HUBACCELERATOR_BUCKET", default="fallback") == "bucket-from-new-name"

    def test_legacy_name_falls_back(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        # Legacy CSV_SECURITYHUB_BUCKET should be picked up if the new name
        # isn't set — with a deprecation warning.
        monkeypatch.setenv("CSV_SECURITYHUB_BUCKET", "legacy-bucket")
        assert env("HUBACCELERATOR_BUCKET", default="fallback") == "legacy-bucket"


# ---------------------------------------------------------------------------
# error_code() — extract botocore ClientError code, or fall back to type name.
# ---------------------------------------------------------------------------


class TestErrorCode:
    def test_botocore_clienterror_shape(self) -> None:
        class FakeClientError(Exception):
            pass

        e = FakeClientError("boom")
        e.response = {"Error": {"Code": "InvalidClientTokenId", "Message": "no creds"}}
        assert error_code(e) == "InvalidClientTokenId"

    def test_unknown_when_response_missing_code(self) -> None:
        class FakeClientError(Exception):
            pass

        e = FakeClientError("boom")
        e.response = {}
        assert error_code(e) == "UNKNOWN"

    def test_falls_back_to_type_name(self) -> None:
        e = ValueError("not an aws error")
        assert error_code(e) == "ValueError"
