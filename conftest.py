"""Fail the test session when a test is skipped.

The mode is opt-in: pass ``--fail-on-skip`` or set
``SCANTPAPER_FAIL_ON_SKIP=1``. Without either switch, a skip keeps its
normal pytest outcome.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

    from pluggy import Result

_ENV_VAR = "SCANTPAPER_FAIL_ON_SKIP"
_ENABLED_ATTR = "_fail_on_skip_enabled"
_STORE_ATTR = "_fail_on_skip_skips"
_SKIP_LONGREPR_LENGTH = 3


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the opt-in switch."""
    parser.addoption(
        "--fail-on-skip",
        action="store_true",
        default=False,
        help="fail the session when any test is skipped",
    )


def _fail_on_skip_enabled(config: pytest.Config) -> bool:
    """Return whether skip-failure mode is active."""
    return bool(config.getoption("fail_on_skip")) or (os.environ.get(_ENV_VAR) == "1")


def pytest_configure(config: pytest.Config) -> None:
    """Record the mode and start a per-session skip store."""
    setattr(config, _ENABLED_ATTR, _fail_on_skip_enabled(config))
    setattr(config, _STORE_ATTR, {})


def pytest_report_header(config: pytest.Config) -> str | None:
    """Announce the mode in the session header."""
    if getattr(config, _ENABLED_ATTR, False):
        return "fail on skip: enabled"
    return None


def _skip_reason(report: pytest.TestReport) -> str:
    """Return the reason from a skipped report."""
    longrepr = report.longrepr
    if isinstance(longrepr, tuple) and len(longrepr) >= _SKIP_LONGREPR_LENGTH:
        return str(longrepr[2])
    return report.longreprtext


def _store(config: pytest.Config) -> dict[str, str]:
    """Return the per-session skip store."""
    return cast("dict[str, str]", getattr(config, _STORE_ATTR))


def _failure_lines(skips: dict[str, str]) -> list[str]:
    """Build the strict-mode failure report."""
    lines = [f"[FAIL] {len(skips)} test(s) skipped while fail-on-skip is enabled:"]
    for nodeid, reason in sorted(skips.items()):
        lines.append(f"  {nodeid}")
        lines.append(f"    {reason}")
    return lines


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
) -> Generator[None, Result[pytest.TestReport], None]:
    """Record a skipped setup or call report."""
    outcome = yield
    report = outcome.get_result()
    if (
        report.skipped
        and getattr(report, "wasxfail", None) is None
        and report.when in ("setup", "call")
    ):
        _store(item.config).setdefault(report.nodeid, _skip_reason(report))


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter,
    config: pytest.Config,
) -> None:
    """Print every skipped test when strict mode is active."""
    if not getattr(config, _ENABLED_ATTR, False):
        return
    skips = _store(config)
    if not skips:
        return
    for line in _failure_lines(skips):
        terminalreporter.write_line(line)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Fail the session when strict mode recorded a skip."""
    config = session.config
    if not getattr(config, _ENABLED_ATTR, False):
        return
    if getattr(config, "workerinput", None) is not None:
        return
    skips = _store(config)
    if not skips:
        return
    if config.pluginmanager.getplugin("terminalreporter") is None:
        sys.stderr.write("\n".join(_failure_lines(skips)) + "\n")
    if exitstatus == pytest.ExitCode.OK:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
