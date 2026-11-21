"""Tests for the linter release check dev/check_linters.py."""

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


class ToolJson(TypedDict):
    """One tool's entry in the JSON report."""

    pinned: str
    installed: str | None
    latest: str
    state: str
    changed: bool
    warnings: list[str]
    validations: list[ValidationJson]


class PayloadJson(TypedDict):
    """The JSON report the tool emits with --json."""

    tools: dict[str, ToolJson]
    state: str
    changed: bool
    markdown: str
    summary: str


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CHECK = REPO_ROOT / "dev" / "check_linters.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "test.yml"

_PASS = f"{sys.executable} -c \"print('all good')\""
_FAIL = f"{sys.executable} -c \"import sys; print('boom'); sys.exit(3)\""


def _registry(tmp_path: Path, tool: str, version: str | None) -> str:
    """Write a PyPI-style registry document and return its file:// URL."""
    document: dict[str, object] = {"name": tool, "info": {}}
    if version is not None:
        document["info"] = {"version": version}
    path = tmp_path / f"{tool}.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path.as_uri()


def _run(
    tmp_path: Path,
    *flags: str,
    pins: dict[str, str] | None = None,
    registry_versions: dict[str, str | None] | None = None,
    registry_urls: dict[str, str] | None = None,
    commands: dict[str, tuple[str, ...]] | None = None,
    installed: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run dev/check_linters.py over file:// fixtures in ``tmp_path``."""
    pin_path = tmp_path / "lint-versions"
    pin_path.write_text(
        "".join(f"{tool}={version}\n" for tool, version in (pins or {}).items()),
        encoding="utf-8",
    )
    args = [
        sys.executable,
        str(CHECK),
        "--pin-file",
        str(pin_path),
        "--cwd",
        str(tmp_path),
    ]
    for tool, version in (registry_versions or {}).items():
        args += ["--registry-url", f"{tool}={_registry(tmp_path, tool, version)}"]
    for tool, url in (registry_urls or {}).items():
        args += ["--registry-url", f"{tool}={url}"]
    for tool, versions in (installed or {}).items():
        args += ["--installed", f"{tool}={versions}"]
    for tool, tool_commands in (commands or {}).items():
        for command in tool_commands:
            args += ["--validate-cmd", f"{tool}={command}"]
    args += list(flags)
    return subprocess.run(args, capture_output=True, text=True, check=False)


def _payload(result: subprocess.CompletedProcess[str]) -> PayloadJson:
    """Return the --json report as a typed dict."""
    return cast("PayloadJson", json.loads(result.stdout))


def _load_check() -> ModuleType:
    """Import dev/check_linters.py directly, bypassing the dev namespace."""
    spec = importlib.util.spec_from_file_location("cl", str(CHECK))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["cl"] = module
    spec.loader.exec_module(module)
    return module


def test_parse_version_accepts_release_and_prerelease() -> None:
    """Release versions compare by their numeric parts."""
    check = _load_check()
    assert check.parse_version("0.16.7") == (0, 16, 7)
    assert check.parse_version(" 1.0.1-rc1 ") == (1, 0, 1)


def test_read_pins_parses_every_tool_line(tmp_path: Path) -> None:
    """The pin file maps each tool to its version."""
    pins = {"ruff": "0.16.7", "ty": "0.0.85"}
    pin_path = tmp_path / "lint-versions"
    pin_path.write_text("ruff=0.16.7\nty=0.0.85\n", encoding="utf-8")
    check = _load_check()
    assert check.read_pins(pin_path) == pins


def test_read_pins_skips_blank_lines(tmp_path: Path) -> None:
    """Blank lines in the pin file are tolerated."""
    pin_path = tmp_path / "lint-versions"
    pin_path.write_text("\nruff=0.16.7\n\n", encoding="utf-8")
    check = _load_check()
    assert check.read_pins(pin_path) == {"ruff": "0.16.7"}


def test_default_validation_commands_are_the_commands_ci_runs() -> None:
    """The defaults cannot drift from the workflow that gates pushes."""
    check = _load_check()
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert check.DEFAULT_VALIDATE_COMMANDS["ruff"] == (
        "ruff check .",
        "ruff format --check .",
    )
    assert check.DEFAULT_VALIDATE_COMMANDS["ty"] == ("ty check .",)
    for commands in check.DEFAULT_VALIDATE_COMMANDS.values():
        for command in commands:
            assert command in workflow


def test_current_pins_report_nothing_to_do(tmp_path: Path) -> None:
    """Pins matching the registry report the current state."""
    result = _run(
        tmp_path,
        "--json",
        pins={"ruff": "0.16.7", "ty": "0.0.85"},
        registry_versions={"ruff": "0.16.7", "ty": "0.0.85"},
        installed={"ruff": "0.16.7", "ty": "0.0.85"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["state"] == "current"
    assert payload["changed"] is False
    assert payload["tools"]["ruff"]["validations"] == []
    assert payload["tools"]["ty"]["validations"] == []
    assert "nothing to do" in payload["markdown"]
    assert "up to date: nothing to do" in payload["summary"]


def test_pin_ahead_of_the_registry_is_current(tmp_path: Path) -> None:
    """A pin newer than PyPI's latest is not reported as a downgrade."""
    result = _run(
        tmp_path,
        "--json",
        pins={"ruff": "0.17.0"},
        registry_versions={"ruff": "0.16.7"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert _payload(result)["tools"]["ruff"]["state"] == "current"


def test_validating_candidate_is_safe_to_upgrade(tmp_path: Path) -> None:
    """A candidate that passes every command is safe to upgrade."""
    result = _run(
        tmp_path,
        "--json",
        pins={"ruff": "0.16.7"},
        registry_versions={"ruff": "0.17.0"},
        commands={"ruff": (_PASS,)},
        installed={"ruff": "0.16.7"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["tools"]["ruff"]["state"] == "update-safe"
    assert payload["tools"]["ruff"]["changed"] is True
    assert payload["tools"]["ruff"]["pinned"] == "0.16.7"
    assert payload["tools"]["ruff"]["latest"] == "0.17.0"
    assert payload["tools"]["ruff"]["validations"][0]["ok"] is True
    assert "safe to upgrade" in payload["markdown"]
    assert "dev/lint-versions" in payload["markdown"]


def test_failing_validation_blocks_the_update(tmp_path: Path) -> None:
    """A failing command blocks the update and its output is recorded."""
    result = _run(
        tmp_path,
        "--json",
        pins={"ty": "0.0.85"},
        registry_versions={"ty": "0.0.86"},
        commands={"ty": (_PASS, _FAIL)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["tools"]["ty"]["state"] == "update-blocked"
    validations = payload["tools"]["ty"]["validations"]
    assert [entry["ok"] for entry in validations] == [True, False]
    assert validations[1]["returncode"] == 3
    assert "boom" in validations[1]["output"]
    assert "fail (exit 3)" in payload["markdown"]
    assert "boom" in payload["markdown"]


def test_validation_stops_at_the_first_failure(tmp_path: Path) -> None:
    """A later command is not run once one has failed."""
    result = _run(
        tmp_path,
        "--json",
        pins={"ruff": "0.16.7"},
        registry_versions={"ruff": "0.17.0"},
        commands={"ruff": (_FAIL, _PASS)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(_payload(result)["tools"]["ruff"]["validations"]) == 1


def test_tools_are_classified_independently(tmp_path: Path) -> None:
    """Ruff can be safe while ty is blocked in the same report."""
    result = _run(
        tmp_path,
        "--json",
        pins={"ruff": "0.16.7", "ty": "0.0.85"},
        registry_versions={"ruff": "0.17.0", "ty": "0.0.86"},
        commands={"ruff": (_PASS,), "ty": (_FAIL,)},
        installed={"ruff": "0.16.7", "ty": "0.0.85"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["tools"]["ruff"]["state"] == "update-safe"
    assert payload["tools"]["ty"]["state"] == "update-blocked"
    assert payload["state"] == "update-blocked"


def test_config_migration_warning_is_surfaced(tmp_path: Path) -> None:
    """Exit-zero-with-warnings stays safe but the warning is reported."""
    warn = (
        f'{sys.executable} -c "import sys; '
        "print('warning: setting `lint.ignore` entry has been removed')\""
    )
    result = _run(
        tmp_path,
        "--json",
        pins={"ruff": "0.16.7"},
        registry_versions={"ruff": "0.17.0"},
        commands={"ruff": (warn,)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["tools"]["ruff"]["state"] == "update-safe"
    warnings = payload["tools"]["ruff"]["warnings"]
    assert warnings
    assert "has been removed" in warnings[0]
    assert "Config-migration warnings" in payload["markdown"]


def test_exit_code_is_two_for_a_missing_pin_file(tmp_path: Path) -> None:
    """An unreadable pin is a state the tool cannot report."""
    result = _run(tmp_path, "--pin-file", str(tmp_path / "absent"))
    assert result.returncode == 2
    assert "cannot read the pin file" in result.stderr


def test_exit_code_is_two_for_an_empty_pin_file(tmp_path: Path) -> None:
    """An empty pin file does not name any tool."""
    pin_path = tmp_path / "lint-versions"
    pin_path.write_text("", encoding="utf-8")
    result = _run(tmp_path, "--pin-file", str(pin_path))
    assert result.returncode == 2
    assert "is empty" in result.stderr


def test_exit_code_is_two_for_an_unreadable_registry(tmp_path: Path) -> None:
    """An unreachable registry is never reported as up to date."""
    missing = (tmp_path / "absent.json").as_uri()
    result = _run(
        tmp_path,
        "--json",
        pins={"ruff": "0.16.7"},
        registry_urls={"ruff": missing},
    )
    assert result.returncode == 2
    assert "cannot read" in result.stderr


def test_registry_without_a_version_fails(tmp_path: Path) -> None:
    """A registry document without a version cannot answer the question."""
    result = _run(
        tmp_path,
        "--json",
        pins={"ruff": "0.16.7"},
        registry_versions={"ruff": None},
    )
    assert result.returncode == 2
    assert "did not report a 'version' string" in result.stderr


def test_tool_filter_selects_one_tool(tmp_path: Path) -> None:
    """--tool ruff checks only ruff, even when ty is pinned."""
    result = _run(
        tmp_path,
        "--json",
        "--tool",
        "ruff",
        pins={"ruff": "0.16.7", "ty": "0.0.85"},
        registry_versions={"ruff": "0.17.0", "ty": "0.0.86"},
        commands={"ruff": (_PASS,)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert set(payload["tools"]) == {"ruff"}


def test_unknown_tool_filter_fails(tmp_path: Path) -> None:
    """--tool naming a tool not in the pin file cannot be reported."""
    result = _run(
        tmp_path,
        "--tool",
        "mypy",
        pins={"ruff": "0.16.7"},
        registry_versions={"ruff": "0.17.0"},
    )
    assert result.returncode == 2
    assert "not in the pin file" in result.stderr


def test_human_output_names_each_state(tmp_path: Path) -> None:
    """The default output is readable without --json."""
    result = _run(
        tmp_path,
        pins={"ruff": "0.16.7"},
        registry_versions={"ruff": "0.17.0"},
        commands={"ruff": (_PASS,)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "overall update-safe" in result.stdout
    assert "update available: safe to upgrade" in result.stdout


def test_markdown_reports_the_installed_version(tmp_path: Path) -> None:
    """The report distinguishes the pin from whatever ran the check."""
    result = _run(
        tmp_path,
        "--markdown",
        pins={"ruff": "0.16.7"},
        registry_versions={"ruff": "0.16.7"},
        installed={"ruff": "0.16.5"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "`0.16.5`" in result.stdout
