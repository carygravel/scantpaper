"""Repository layout and coverage-configuration checks.

The application gate measures only the shipped package, so developer-tooling
tests live under ``dev/tests`` next to the scripts they exercise. Test
execution data is still recorded and audited separately, which requires the
exclusion to stay at report level rather than run level.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import cast

from scantpaper.const import tomllib

REPO_ROOT = Path(__file__).resolve().parents[3]
PYPROJECT = REPO_ROOT / "pyproject.toml"
APP_TESTS = REPO_ROOT / "src" / "scantpaper" / "tests"
DEV_TESTS = REPO_ROOT / "dev" / "tests"

DEV_TOOL_TESTS = (
    "test_build_ppa.py",
    "test_launchpad.py",
    "test_prepare_deb.py",
    "test_prepare_rpm.py",
    "test_release.py",
    "test_strip_remote_images.py",
    "test_sync_salsa.py",
)

MIXED_MODULES = (
    "test_openspec_specs.py",
    "test_po_files.py",
)

COVERAGE_THRESHOLD = 99


def _tool_table() -> dict[str, object]:
    """Return the ``[tool]`` table from pyproject.toml."""
    text = PYPROJECT.read_text(encoding="utf-8")
    parsed = cast("dict[str, object]", tomllib.loads(text))
    return cast("dict[str, object]", parsed["tool"])


def test_dev_tool_tests_live_with_the_tools() -> None:
    """Every dev-script test module lives under dev/tests only."""
    for name in DEV_TOOL_TESTS:
        assert (DEV_TESTS / name).is_file(), f"missing dev/tests/{name}"
        assert not (APP_TESTS / name).exists(), (
            f"{name} belongs in dev/tests, not the package"
        )


def test_mixed_modules_stay_with_the_application() -> None:
    """Modules that also validate shipped data remain in the package tree."""
    for name in MIXED_MODULES:
        assert (APP_TESTS / name).is_file(), f"missing src/scantpaper/tests/{name}"


def _is_omitted(sample: str, patterns: list[str]) -> bool:
    """Return whether ``sample`` matches any report omit pattern."""
    return any(fnmatch.fnmatch(sample, pattern) for pattern in patterns)


def test_test_code_is_omitted_from_the_report_not_the_run() -> None:
    """The gate reports application code while the audit data is kept."""
    coverage = cast("dict[str, object]", _tool_table()["coverage"])
    run = cast("dict[str, object]", coverage["run"])
    report = cast("dict[str, object]", coverage["report"])

    assert "omit" not in run, "run-level omit discards the audit data"
    assert run["branch"] is True

    omit = cast("list[str]", report["omit"])
    app_sample = str(APP_TESTS / "test_coverage_config.py")
    dev_sample = str(DEV_TESTS / "test_check_test_coverage.py")
    assert _is_omitted(app_sample, omit), f"{app_sample} is not omitted"
    assert _is_omitted(dev_sample, omit), f"{dev_sample} is not omitted"


def test_coverage_threshold_is_ninety_nine() -> None:
    """The application gate keeps the 99% threshold."""
    pytest_table = cast("dict[str, object]", _tool_table()["pytest"])
    options = cast("dict[str, object]", pytest_table["ini_options"])
    addopts = cast("str", options["addopts"])
    assert f"--cov-fail-under={COVERAGE_THRESHOLD}" in addopts
