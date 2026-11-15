"""Tests for i18n helpers."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scantpaper import const


def _distribution(name: str | None, version: str | None) -> SimpleNamespace:
    """Build a fake installed distribution."""
    return SimpleNamespace(metadata={"Name": name, "Version": version}, version=version)


@pytest.mark.skipif(sys.version_info < (3, 11), reason="Requires Python 3.11 or higher")
def test_import_tomllib_for_python_311(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock sys.version_info to simulate Python 3.11+."""
    monkeypatch.setattr(sys, "version_info", (3, 11))

    # Reload the const module to apply the mocked version_info
    import importlib  # noqa: PLC0415

    from scantpaper import const  # noqa: PLC0415

    importlib.reload(const)

    # Check if tomllib is imported
    assert const.tomllib.__name__ == "tomllib"


def test_import_tomli_for_python_310(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock sys.version_info to simulate Python < 3.11."""
    monkeypatch.setattr(sys, "version_info", (3, 10))

    # Reload the const module to apply the mocked version_info
    import importlib  # noqa: PLC0415

    from scantpaper import const  # noqa: PLC0415

    importlib.reload(const)

    # Check if tomli is imported as tomllib
    assert const.tomllib.__name__ == "tomli"


def test_get_metadata() -> None:
    """Test getting metadata."""
    with (
        patch("importlib.metadata.version", side_effect="l"),
        patch("pathlib.Path.is_file", return_value=False),
    ):
        assert const.get_version() == "l"


def test_get_version_from_pyproject() -> None:
    """Read the version from a source checkout."""
    pyproject = '[project]\nversion = "4.0.4"\n'
    with (
        patch("pathlib.Path.is_file", return_value=True),
        patch("pathlib.Path.read_text", return_value=pyproject),
    ):
        assert const.get_version() == "4.0.4"


def test_get_version_recovers_from_stale_metadata() -> None:
    """Skip an empty stale distribution and use the valid one."""
    distributions = [
        _distribution("other-package", "1.0"),
        _distribution(None, None),
        _distribution(const.PROG_NAME, "4.0.4"),
    ]
    with (
        patch("pathlib.Path.is_file", return_value=False),
        patch("importlib.metadata.version", return_value=None),
        patch("importlib.metadata.distributions", return_value=distributions),
    ):
        assert const.get_version() == "4.0.4"


def test_get_version_recovers_when_metadata_version_is_empty() -> None:
    """Treat an empty metadata version as missing and keep scanning."""
    distributions = [_distribution(const.PROG_NAME, "4.0.4")]
    with (
        patch("pathlib.Path.is_file", return_value=False),
        patch("importlib.metadata.version", return_value=""),
        patch("importlib.metadata.distributions", return_value=distributions),
    ):
        assert const.get_version() == "4.0.4"


def test_get_version_unknown_when_package_missing() -> None:
    """Fall back when no matching distribution is installed."""
    missing = const.importlib.metadata.PackageNotFoundError(const.PROG_NAME)
    with (
        patch("pathlib.Path.is_file", return_value=False),
        patch("importlib.metadata.version", side_effect=missing),
        patch("importlib.metadata.distributions", return_value=[]),
    ):
        assert const.get_version() == const.UNKNOWN_VERSION


def test_get_version_unknown_when_all_metadata_empty() -> None:
    """Fall back when every matching distribution lacks a version."""
    distributions = [
        _distribution("other-package", "1.0"),
        _distribution(None, None),
    ]
    with (
        patch("pathlib.Path.is_file", return_value=False),
        patch("importlib.metadata.version", return_value=None),
        patch("importlib.metadata.distributions", return_value=distributions),
    ):
        assert const.get_version() == const.UNKNOWN_VERSION
