"""Tests for the root fail-on-skip conftest."""

from __future__ import annotations

import contextlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_root_conftest() -> ModuleType:
    """Import the repository-root conftest as a module."""
    spec = importlib.util.spec_from_file_location(
        "root_conftest", REPO_ROOT / "conftest.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT_CONFTEST = _load_root_conftest()


@pytest.fixture(autouse=True)
def _clear_fail_on_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the developer's switch out of the hook tests."""
    monkeypatch.delenv(ROOT_CONFTEST._ENV_VAR, raising=False)


def _config(
    *,
    enabled: bool = False,
    store: dict[str, str] | None = None,
    option: bool = False,
    worker: bool = False,
) -> SimpleNamespace:
    """Build a minimal pytest config for the hook tests."""
    config = SimpleNamespace(
        getoption=lambda _name: option,
        pluginmanager=SimpleNamespace(getplugin=lambda _name: None),
    )
    setattr(config, ROOT_CONFTEST._ENABLED_ATTR, enabled)
    setattr(config, ROOT_CONFTEST._STORE_ATTR, {} if store is None else store)
    if worker:
        config.workerinput = {}
    return config


def _session(
    config: SimpleNamespace, exitstatus: int = pytest.ExitCode.OK
) -> SimpleNamespace:
    """Build a minimal pytest session for the finish hook tests."""
    return SimpleNamespace(config=config, exitstatus=exitstatus)


def _makereport(item: SimpleNamespace, report: SimpleNamespace) -> None:
    """Run the hookwrapper to completion with a fake report."""
    outcome = SimpleNamespace(get_result=lambda: report)
    generator = cast(
        "Generator[None, object, None]",
        ROOT_CONFTEST.pytest_runtest_makereport(item),
    )
    next(generator)
    with contextlib.suppress(StopIteration):
        generator.send(outcome)


def test_fail_on_skip_enabled_flag() -> None:
    """The flag enables the mode."""
    assert ROOT_CONFTEST._fail_on_skip_enabled(_config(option=True)) is True


def test_fail_on_skip_enabled_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The environment variable enables the mode."""
    monkeypatch.setenv(ROOT_CONFTEST._ENV_VAR, "1")
    assert ROOT_CONFTEST._fail_on_skip_enabled(_config()) is True


def test_fail_on_skip_enabled_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """The string zero does not enable the mode."""
    monkeypatch.setenv(ROOT_CONFTEST._ENV_VAR, "0")
    assert ROOT_CONFTEST._fail_on_skip_enabled(_config()) is False


def test_fail_on_skip_enabled_both(monkeypatch: pytest.MonkeyPatch) -> None:
    """Either switch is enough when both are set."""
    monkeypatch.setenv(ROOT_CONFTEST._ENV_VAR, "1")
    assert ROOT_CONFTEST._fail_on_skip_enabled(_config(option=True)) is True


def test_fail_on_skip_enabled_neither() -> None:
    """Neither switch leaves the mode off."""
    assert ROOT_CONFTEST._fail_on_skip_enabled(_config()) is False


def test_configure_initialises_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """The configure hook records the mode and an empty store."""
    monkeypatch.setenv(ROOT_CONFTEST._ENV_VAR, "1")
    config = _config()
    ROOT_CONFTEST.pytest_configure(config)
    assert getattr(config, ROOT_CONFTEST._ENABLED_ATTR) is True
    assert getattr(config, ROOT_CONFTEST._STORE_ATTR) == {}


def test_report_header_enabled() -> None:
    """The header announces the active mode."""
    assert (
        ROOT_CONFTEST.pytest_report_header(_config(enabled=True))
        == "fail on skip: enabled"
    )


def test_report_header_disabled() -> None:
    """The header is absent when the mode is off."""
    assert ROOT_CONFTEST.pytest_report_header(_config(enabled=False)) is None


def test_skip_reason_tuple() -> None:
    """A tuple longrepr exposes its reason."""
    report = SimpleNamespace(
        longrepr=("file.py", 1, "marker reason"),
        longreprtext="ignored",
    )
    assert ROOT_CONFTEST._skip_reason(report) == "marker reason"


def test_skip_reason_string() -> None:
    """A string longrepr falls back to longreprtext."""
    report = SimpleNamespace(longrepr="plain reason", longreprtext="plain reason")
    assert ROOT_CONFTEST._skip_reason(report) == "plain reason"


def test_skip_reason_short_tuple() -> None:
    """A short tuple falls back to longreprtext."""
    report = SimpleNamespace(longrepr=("file.py", 1), longreprtext="fallback")
    assert ROOT_CONFTEST._skip_reason(report) == "fallback"


def test_makereport_setup_skip() -> None:
    """A skipped setup report is recorded."""
    item = SimpleNamespace(config=_config(store={}))
    report = SimpleNamespace(
        skipped=True,
        when="setup",
        nodeid="test.py::test_x",
        longrepr=("file.py", 1, "reason"),
        longreprtext="reason",
    )
    _makereport(item, report)
    assert getattr(item.config, ROOT_CONFTEST._STORE_ATTR) == {
        "test.py::test_x": "reason"
    }


def test_makereport_call_skip() -> None:
    """A skipped call report is recorded."""
    item = SimpleNamespace(config=_config(store={}))
    report = SimpleNamespace(
        skipped=True,
        when="call",
        nodeid="test.py::test_x",
        longrepr=("file.py", 1, "reason"),
        longreprtext="reason",
    )
    _makereport(item, report)
    assert getattr(item.config, ROOT_CONFTEST._STORE_ATTR) == {
        "test.py::test_x": "reason"
    }


def test_makereport_ignores_other_phases() -> None:
    """A teardown skip is not recorded."""
    item = SimpleNamespace(config=_config(store={}))
    report = SimpleNamespace(
        skipped=True,
        when="teardown",
        nodeid="test.py::test_x",
        longrepr=("file.py", 1, "reason"),
        longreprtext="reason",
    )
    _makereport(item, report)
    assert getattr(item.config, ROOT_CONFTEST._STORE_ATTR) == {}


def test_makereport_ignores_passes() -> None:
    """A passing test is not recorded."""
    item = SimpleNamespace(config=_config(store={}))
    report = SimpleNamespace(
        skipped=False,
        when="call",
        nodeid="test.py::test_x",
        longrepr=None,
        longreprtext="",
    )
    _makereport(item, report)
    assert getattr(item.config, ROOT_CONFTEST._STORE_ATTR) == {}


def test_makereport_ignores_xfail() -> None:
    """An expected failure is not recorded as a skip."""
    item = SimpleNamespace(config=_config(store={}))
    report = SimpleNamespace(
        skipped=True,
        wasxfail="expected failure",
        when="call",
        nodeid="test.py::test_x",
        longrepr=("file.py", 1, "expected failure"),
        longreprtext="expected failure",
    )
    _makereport(item, report)
    assert getattr(item.config, ROOT_CONFTEST._STORE_ATTR) == {}


def test_makereport_deduplicates_node_id() -> None:
    """The first reason for a node id is kept."""
    item = SimpleNamespace(config=_config(store={}))
    first = SimpleNamespace(
        skipped=True,
        when="setup",
        nodeid="test.py::test_x",
        longrepr=("file.py", 1, "first"),
        longreprtext="first",
    )
    second = SimpleNamespace(
        skipped=True,
        when="call",
        nodeid="test.py::test_x",
        longrepr=("file.py", 1, "second"),
        longreprtext="second",
    )
    _makereport(item, first)
    _makereport(item, second)
    assert getattr(item.config, ROOT_CONFTEST._STORE_ATTR) == {
        "test.py::test_x": "first"
    }


def test_terminal_summary_lists_each_skip() -> None:
    """The summary names every node id and reason."""
    reporter = MagicMock()
    config = _config(
        enabled=True,
        store={"a.py::test_a": "reason a", "b.py::test_b": "reason b"},
    )
    ROOT_CONFTEST.pytest_terminal_summary(reporter, config)
    lines = [call.args[0] for call in reporter.write_line.call_args_list]
    assert any("a.py::test_a" in line for line in lines)
    assert any("reason a" in line for line in lines)
    assert any("b.py::test_b" in line for line in lines)
    assert any("reason b" in line for line in lines)


def test_terminal_summary_disabled() -> None:
    """A disabled run prints nothing."""
    reporter = MagicMock()
    ROOT_CONFTEST.pytest_terminal_summary(
        reporter, _config(enabled=False, store={"a": "b"})
    )
    reporter.write_line.assert_not_called()


def test_terminal_summary_empty() -> None:
    """A run with no skips prints nothing."""
    reporter = MagicMock()
    ROOT_CONFTEST.pytest_terminal_summary(reporter, _config(enabled=True, store={}))
    reporter.write_line.assert_not_called()


def test_sessionfinish_fails_ok_session() -> None:
    """An OK session with a recorded skip fails."""
    config = _config(enabled=True, store={"test.py::test_x": "reason"})
    config.pluginmanager = SimpleNamespace(getplugin=lambda _name: object())
    session = _session(config)
    ROOT_CONFTEST.pytest_sessionfinish(session, pytest.ExitCode.OK)
    assert session.exitstatus == pytest.ExitCode.TESTS_FAILED


def test_sessionfinish_preserves_failure() -> None:
    """An existing non-zero status is not replaced."""
    config = _config(enabled=True, store={"test.py::test_x": "reason"})
    config.pluginmanager = SimpleNamespace(getplugin=lambda _name: object())
    session = _session(config, exitstatus=2)
    ROOT_CONFTEST.pytest_sessionfinish(session, 2)
    assert session.exitstatus == 2


def test_sessionfinish_disabled() -> None:
    """A disabled session is left alone."""
    session = _session(_config(enabled=False, store={"test.py::test_x": "reason"}))
    ROOT_CONFTEST.pytest_sessionfinish(session, pytest.ExitCode.OK)
    assert session.exitstatus == pytest.ExitCode.OK


def test_sessionfinish_no_skips() -> None:
    """A session with no skips is left alone."""
    session = _session(_config(enabled=True, store={}))
    ROOT_CONFTEST.pytest_sessionfinish(session, pytest.ExitCode.OK)
    assert session.exitstatus == pytest.ExitCode.OK


def test_sessionfinish_worker() -> None:
    """An xdist worker does not set the exit status."""
    session = _session(
        _config(enabled=True, store={"test.py::test_x": "reason"}, worker=True)
    )
    ROOT_CONFTEST.pytest_sessionfinish(session, pytest.ExitCode.OK)
    assert session.exitstatus == pytest.ExitCode.OK


def test_sessionfinish_without_terminal(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The failure report is written to stderr when no reporter exists."""
    session = _session(_config(enabled=True, store={"test.py::test_x": "reason"}))
    ROOT_CONFTEST.pytest_sessionfinish(session, pytest.ExitCode.OK)
    assert session.exitstatus == pytest.ExitCode.TESTS_FAILED
    assert "test.py::test_x" in capsys.readouterr().err


def test_addoption_registers_flag() -> None:
    """The option is registered under the documented name."""
    parser = MagicMock()
    ROOT_CONFTEST.pytest_addoption(parser)
    parser.addoption.assert_called_once()
    assert parser.addoption.call_args.args[0] == "--fail-on-skip"


SKIP_TESTS = """
import pytest


@pytest.mark.skip(reason="marker skip")
def test_marker_skip() -> None:
    assert False


def test_import_skip() -> None:
    pytest.importorskip("a_module_that_does_not_exist")
"""

DESELECT_TESTS = """
import pytest


def test_ok() -> None:
    assert True


@pytest.mark.slow
def test_slow_skip() -> None:
    pytest.skip("slow skip")
"""

IGNORED_TESTS = """
import pytest


def test_ignored_skip() -> None:
    pytest.skip("ignored skip")
"""

OK_TESTS = """
def test_ok() -> None:
    assert True
"""

XFAIL_TESTS = """
import pytest


def test_ok() -> None:
    assert True


@pytest.mark.xfail(reason="expected failure")
def test_expected_failure() -> None:
    assert False
"""


def _prepare(tmp_path: Path, files: dict[str, str]) -> Path:
    """Copy the root conftest and the given test files into a temp project."""
    project = tmp_path / "project"
    project.mkdir()
    shutil.copy(REPO_ROOT / "conftest.py", project / "conftest.py")
    for name, content in files.items():
        (project / name).write_text(content, encoding="utf-8")
    return project


def _run(
    project: Path, *args: str, strict: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run pytest in a temporary project and return the completed process."""
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    env.pop(ROOT_CONFTEST._ENV_VAR, None)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    if strict:
        env[ROOT_CONFTEST._ENV_VAR] = "1"
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *args],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_and_env_select_strict_mode(tmp_path: Path) -> None:
    """Both switches fail the session for marker and import skips."""
    project = _prepare(tmp_path, {"test_skips.py": SKIP_TESTS})
    default = _run(project)
    assert default.returncode == 0, default.stdout
    flag = _run(project, "--fail-on-skip")
    assert flag.returncode == 1, flag.stdout
    assert "marker skip" in flag.stdout
    assert "a_module_that_does_not_exist" in flag.stdout
    env = _run(project, strict=True)
    assert env.returncode == 1, env.stdout
    both = _run(project, "--fail-on-skip", strict=True)
    assert both.returncode == 1, both.stdout


def test_deselected_test_does_not_fail(tmp_path: Path) -> None:
    """A marker-deselected test is not a skip."""
    project = _prepare(tmp_path, {"test_deselect.py": DESELECT_TESTS})
    result = _run(project, "--fail-on-skip", "-m", "not slow")
    assert result.returncode == 0, result.stdout


def test_ignored_test_does_not_fail(tmp_path: Path) -> None:
    """An ignored test is not a skip."""
    project = _prepare(
        tmp_path,
        {"test_ok.py": OK_TESTS, "test_ignored.py": IGNORED_TESTS},
    )
    result = _run(project, "--fail-on-skip", "--ignore=test_ignored.py")
    assert result.returncode == 0, result.stdout


def test_expected_failure_does_not_fail(tmp_path: Path) -> None:
    """An xfailed test is not a skip."""
    project = _prepare(tmp_path, {"test_xfail.py": XFAIL_TESTS})
    result = _run(project, "--fail-on-skip")
    assert result.returncode == 0, result.stdout
