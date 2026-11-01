"""Tests for the OpenSpec release check dev/check_openspec.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, cast

if TYPE_CHECKING:
    from types import ModuleType


class ValidationJson(TypedDict):
    """One validation command's entry in the JSON report."""

    command: str
    ok: bool
    returncode: int
    output: str


class PayloadJson(TypedDict):
    """The JSON report the tool emits with --json."""

    pinned: str
    installed: str | None
    latest: str
    state: str
    changed: bool
    validations: list[ValidationJson]
    markdown: str
    summary: str


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CHECK = REPO_ROOT / "dev" / "check_openspec.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "test.yml"

_PASS = f"{sys.executable} -c \"print('all good')\""
_FAIL = f"{sys.executable} -c \"import sys; print('boom'); sys.exit(3)\""


def _registry(tmp_path: Path, version: str | None) -> str:
    """Write a registry document and return its file:// URL."""
    document: dict[str, str] = {"name": "@fission-ai/openspec"}
    if version is not None:
        document["version"] = version
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path.as_uri()


def _run(
    tmp_path: Path,
    *flags: str,
    pin: str = "1.14.3\n",
    registry_version: str | None = "1.16.0",
    commands: tuple[str, ...] = (_PASS,),
    installed: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run dev/check_openspec.py over file:// fixtures in ``tmp_path``."""
    pin_path = tmp_path / "openspec-version"
    pin_path.write_text(pin, encoding="utf-8")
    args = [
        sys.executable,
        str(CHECK),
        "--pin-file",
        str(pin_path),
        "--registry-url",
        _registry(tmp_path, registry_version),
        "--cwd",
        str(tmp_path),
    ]
    if installed is not None:
        args += ["--installed", installed]
    for command in commands:
        args += ["--validate-cmd", command]
    args += list(flags)
    return subprocess.run(args, capture_output=True, text=True, check=False)


def _payload(result: subprocess.CompletedProcess[str]) -> PayloadJson:
    """Return the --json report as a typed dict."""
    return cast("PayloadJson", json.loads(result.stdout))


def _load_check() -> ModuleType:
    """Import dev/check_openspec.py directly, bypassing the dev namespace."""
    spec = importlib.util.spec_from_file_location("co", str(CHECK))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["co"] = module
    spec.loader.exec_module(module)
    return module


def test_parse_version_accepts_release_and_pre_release() -> None:
    """Release versions compare by their numeric parts."""
    check = _load_check()
    assert check.parse_version("1.16.0") == (1, 16, 0)
    assert check.parse_version(" 2.0.1-beta.1 ") == (2, 0, 1)


def test_read_pin_trims_the_trailing_newline(tmp_path: Path) -> None:
    """The pin file may end in a newline, as editable text usually does."""
    pin_path = tmp_path / "openspec-version"
    pin_path.write_text("1.16.0\n", encoding="utf-8")
    check = _load_check()
    assert check.read_pin(pin_path) == "1.16.0"


def test_read_installed_reports_none_for_a_missing_command() -> None:
    """A CLI that is not installed is reported as unknown, not as an error."""
    check = _load_check()
    assert check.read_installed("definitely-not-an-openspec-cli") is None


def test_read_installed_returns_the_command_version() -> None:
    """An installed command reports its version on stdout."""
    check = _load_check()
    assert check.read_installed(sys.executable) is not None


def test_default_validation_commands_are_the_commands_ci_runs() -> None:
    """The defaults cannot drift from the workflow that gates pushes."""
    check = _load_check()
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert check.DEFAULT_VALIDATE_COMMANDS == (
        "openspec validate --specs --strict --no-interactive",
        "openspec validate --archived --no-interactive",
    )
    for command in check.DEFAULT_VALIDATE_COMMANDS:
        assert f"run: {command}" in workflow


def test_current_pin_reports_nothing_to_do(tmp_path: Path) -> None:
    """A pin matching the registry reports the current state."""
    result = _run(tmp_path, "--json", pin="1.16.0\n", registry_version="1.16.0")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["state"] == "current"
    assert payload["changed"] is False
    assert payload["validations"] == []
    assert "nothing to do" in payload["markdown"]
    assert "npm install" not in payload["markdown"]
    assert "up to date: nothing to do" in payload["summary"]


def test_pin_ahead_of_the_registry_is_current(tmp_path: Path) -> None:
    """A pin newer than npm's latest is not reported as a downgrade."""
    result = _run(tmp_path, "--json", pin="1.17.0\n", registry_version="1.16.0")
    assert result.returncode == 0, result.stdout + result.stderr
    assert _payload(result)["state"] == "current"


def test_validating_candidate_is_safe_to_upgrade(tmp_path: Path) -> None:
    """A candidate that passes every command is safe to upgrade."""
    result = _run(tmp_path, "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["state"] == "update-safe"
    assert payload["changed"] is True
    assert payload["pinned"] == "1.14.3"
    assert payload["latest"] == "1.16.0"
    assert [entry["ok"] for entry in payload["validations"]] == [True]
    assert "Safe to upgrade" in payload["markdown"]
    assert "dev/openspec-version" in payload["markdown"]
    assert "npm install -g @fission-ai/openspec@1.16.0" in payload["markdown"]


def test_failing_validation_blocks_the_update(tmp_path: Path) -> None:
    """A failing command blocks the update and its output is recorded."""
    result = _run(tmp_path, "--json", commands=(_PASS, _FAIL))
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["state"] == "update-blocked"
    assert [entry["ok"] for entry in payload["validations"]] == [True, False]
    assert payload["validations"][1]["returncode"] == 3
    assert "boom" in payload["validations"][1]["output"]
    assert "Blocked" in payload["markdown"]
    assert "boom" in payload["markdown"]


def test_validation_stops_at_the_first_failure(tmp_path: Path) -> None:
    """A later command is not run once one has failed."""
    result = _run(tmp_path, "--json", commands=(_FAIL, _PASS))
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(_payload(result)["validations"]) == 1


def test_summary_names_the_failing_command(tmp_path: Path) -> None:
    """The run summary says which command blocked the candidate."""
    result = _run(tmp_path, "--json", commands=(_PASS, _FAIL))
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert "blocked by a failing validation command" in payload["summary"]
    assert f"FAILED (3): {_FAIL}" in payload["summary"]


def test_markdown_reports_the_installed_version(tmp_path: Path) -> None:
    """The report distinguishes the pin from whatever ran the check."""
    result = _run(tmp_path, "--markdown", installed="1.15.0")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "`1.15.0`" in result.stdout


def test_human_output_names_the_state(tmp_path: Path) -> None:
    """The default output is readable without --json."""
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "update available: safe to upgrade" in result.stdout
    assert "ok: " in result.stdout


def test_missing_pin_file_fails(tmp_path: Path) -> None:
    """An unreadable pin is a state the tool cannot report."""
    result = _run(tmp_path, "--pin-file", str(tmp_path / "absent"))
    assert result.returncode == 2
    assert "cannot read the pin file" in result.stderr


def test_empty_pin_file_fails(tmp_path: Path) -> None:
    """An empty pin file is not a version."""
    result = _run(tmp_path, pin="\n")
    assert result.returncode == 2
    assert "is empty" in result.stderr


def test_invalid_pin_version_fails(tmp_path: Path) -> None:
    """A pin that is not a release version fails loudly."""
    result = _run(tmp_path, pin="latest\n")
    assert result.returncode == 2
    assert "is not a release version" in result.stderr


def test_unreadable_registry_fails(tmp_path: Path) -> None:
    """An unreachable registry is never reported as up to date."""
    missing = (tmp_path / "absent.json").as_uri()
    result = _run(tmp_path, "--registry-url", missing)
    assert result.returncode == 2
    assert "cannot read" in result.stderr


def test_registry_without_a_version_fails(tmp_path: Path) -> None:
    """A registry document without a version cannot answer the question."""
    result = _run(tmp_path, registry_version=None)
    assert result.returncode == 2
    assert "did not report a 'version' string" in result.stderr
