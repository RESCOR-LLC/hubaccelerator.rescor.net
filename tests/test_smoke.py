"""Smoke tests — catch obvious breakage in module imports and console-script
entry points before the more substantive tests run."""

from __future__ import annotations


def test_package_imports() -> None:
    """The top-level package and its three submodules import without error."""

    import hubaccelerator
    from hubaccelerator import exporter, objects, updater  # noqa: F401

    assert hasattr(hubaccelerator, "__name__")


def test_exporter_main_callable() -> None:
    """The exporter console-script entry point exists and is callable."""

    from hubaccelerator import exporter

    assert callable(exporter.main)
    assert callable(exporter.lambdaHandler)
    assert callable(exporter.executor)


def test_updater_main_callable() -> None:
    """The updater console-script entry point exists and is callable."""

    from hubaccelerator import updater

    assert callable(updater.main)
    assert callable(updater.lambdaHandler)
    assert callable(updater.executor)


def test_finding_class_present() -> None:
    """Finding and FindingActions are exposed on the objects module."""

    from hubaccelerator import objects

    assert hasattr(objects, "Finding")
    assert hasattr(objects, "FindingActions")
    assert hasattr(objects, "HubActor")
    assert hasattr(objects, "S3Actor")
    assert hasattr(objects, "SsmActor")
