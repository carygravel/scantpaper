"""Tests for the instruction-file gate dev/check_generated_instructions.py."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TypedDict, cast

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CHECK = REPO_ROOT / "dev" / "check_generated_instructions.py"


class ChangeJson(TypedDict):
    """One planned change in the JSON report."""

    path: str
    action: str


class ReportJson(TypedDict):
    """The JSON report the gate emits with --json."""

    state: str
    changes: list[ChangeJson]
    summary: str


def _plan(
    *changes: tuple[str, str], failures: list[str] | None = None
) -> dict[str, object]:
    """Build an ``openspec update --dry-run --json`` document."""
    payload: dict[str, object] = {
        "changes": [{"path": path, "action": action} for path, action in changes]
    }
    if failures is not None:
        payload["failures"] = failures
    return payload


def _stub(tmp_path: Path, payload: object) -> Path:
    """Write an executable that prints ``payload`` as JSON."""
    path = tmp_path / "openspec-stub"
    path.write_text(
        f"#!/usr/bin/env python3\nimport json\nprint(json.dumps({payload!r}))\n",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def _failing_stub(tmp_path: Path) -> Path:
    """Write an executable that fails like a broken CLI."""
    path = tmp_path / "openspec-broken"
    path.write_text(
        "#!/usr/bin/env python3\nimport sys\nprint('boom', file=sys.stderr)\n"
        "sys.exit(3)\n",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def _run(
    root: Path,
    *flags: str,
    openspec: Path | None = None,
    home: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the gate against a stub CLI with ``root`` as the repository."""
    args = [
        sys.executable,
        str(CHECK),
        "--openspec",
        str(openspec or _stub(root, _plan())),
        "--root",
        str(root),
    ]
    args += list(flags)
    env = None
    if home is not None:
        env = {**os.environ, "HOME": str(home)}
    return subprocess.run(args, capture_output=True, text=True, check=False, env=env)


def _report(result: subprocess.CompletedProcess[str]) -> ReportJson:
    """Return the --json report as a typed dict."""
    return cast("ReportJson", json.loads(result.stdout))


def test_repository_change_fails_the_gate(tmp_path: Path) -> None:
    """A stale generated file inside the repository fails the push."""
    target = tmp_path / ".agents" / "skills" / "openspec" / "SKILL.md"
    stub = _stub(tmp_path, _plan((str(target), "update")))
    result = _run(tmp_path, openspec=stub)
    assert result.returncode == 1, result.stdout + result.stderr
    assert str(target) in result.stdout
    assert "openspec update" in result.stdout


def test_outside_repository_path_is_ignored(tmp_path: Path) -> None:
    """The CLI's own config lives in the user's home, not the repository."""
    outside = tmp_path.parent / "home" / "openspec" / "config.json"
    stub = _stub(tmp_path, _plan((str(outside), "update")))
    result = _run(tmp_path, openspec=stub)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "current" in result.stdout


def test_home_relative_path_is_ignored(tmp_path: Path) -> None:
    """A clean HOME reports the CLI config with a leading tilde."""
    root = tmp_path / "repo"
    home = tmp_path / "home"
    root.mkdir()
    home.mkdir()
    stub = _stub(root, _plan(("~/.config/openspec/config.json", "add")))
    result = _run(root, openspec=stub, home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "current" in result.stdout


def test_home_inside_the_repository_is_still_checked(tmp_path: Path) -> None:
    """Expanding a tilde must not become a blanket skip of home paths."""
    root = tmp_path / "repo"
    home = root / "home"
    home.mkdir(parents=True)
    stub = _stub(root, _plan(("~/page.md", "add")))
    result = _run(root, openspec=stub, home=home)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "~/page.md" in result.stdout


def test_several_changes_are_all_named(tmp_path: Path) -> None:
    """Every stale file is reported, not just the first."""
    first = tmp_path / ".agents" / "skills" / "a" / "SKILL.md"
    second = tmp_path / ".agents" / "skills" / "b" / "SKILL.md"
    stub = _stub(tmp_path, _plan((str(first), "add"), (str(second), "delete")))
    result = _run(tmp_path, openspec=stub)
    assert result.returncode == 1
    assert str(first) in result.stdout
    assert str(second) in result.stdout


def test_relative_path_resolves_against_the_root(tmp_path: Path) -> None:
    """A relative path belongs to the root, not to the process's directory."""
    stub = _stub(tmp_path, _plan((".agents/skills/openspec/SKILL.md", "update")))
    result = _run(tmp_path, openspec=stub)
    assert result.returncode == 1, result.stdout + result.stderr
    assert ".agents/skills/openspec/SKILL.md" in result.stdout


def test_mixed_plan_only_fails_on_repository_paths(tmp_path: Path) -> None:
    """A home-directory entry does not mask a stale repository file."""
    inside = tmp_path / ".agents" / "skills" / "openspec" / "SKILL.md"
    outside = tmp_path.parent / "home" / "openspec" / "config.json"
    stub = _stub(tmp_path, _plan((str(outside), "update"), (str(inside), "add")))
    result = _run(tmp_path, openspec=stub)
    assert result.returncode == 1
    assert str(inside) in result.stdout
    assert str(outside) not in result.stdout


def test_clean_plan_passes(tmp_path: Path) -> None:
    """A plan with no changes leaves the push green."""
    result = _run(tmp_path)
    assert result.returncode == 0
    assert "current" in result.stdout


def test_unreadable_cli_fails_loudly(tmp_path: Path) -> None:
    """A CLI that cannot produce a plan is not reported as current."""
    result = _run(tmp_path, openspec=_failing_stub(tmp_path))
    assert result.returncode == 2
    assert "[FAIL]" in result.stderr


def test_missing_cli_fails_loudly(tmp_path: Path) -> None:
    """A CLI that is not installed is not reported as current."""
    result = _run(tmp_path, openspec=tmp_path / "definitely-not-openspec")
    assert result.returncode == 2
    assert "[FAIL]" in result.stderr


def test_invalid_json_fails_loudly(tmp_path: Path) -> None:
    """Output that is not JSON is not reported as current."""
    stub = tmp_path / "openspec-bad-json"
    stub.write_text("#!/usr/bin/env python3\nprint('not json')\n", encoding="utf-8")
    stub.chmod(0o755)
    result = _run(tmp_path, openspec=stub)
    assert result.returncode == 2
    assert "[FAIL]" in result.stderr


def test_reported_failures_fail_loudly(tmp_path: Path) -> None:
    """A plan the CLI could not complete is not reported as current."""
    stub = _stub(tmp_path, _plan(failures=["cannot write .agents/skills"]))
    result = _run(tmp_path, openspec=stub)
    assert result.returncode == 2
    assert "[FAIL]" in result.stderr


def test_json_report_names_the_stale_files(tmp_path: Path) -> None:
    """The machine-readable report carries the state, paths and actions."""
    target = tmp_path / ".agents" / "skills" / "openspec" / "SKILL.md"
    stub = _stub(tmp_path, _plan((str(target), "update")))
    result = _run(tmp_path, "--json", openspec=stub)
    assert result.returncode == 1
    report = _report(result)
    assert report["state"] == "stale"
    assert report["changes"] == [{"path": str(target), "action": "update"}]
    assert str(target) in report["summary"]


def test_json_report_is_current_when_nothing_is_stale(tmp_path: Path) -> None:
    """A clean plan reports a current state."""
    result = _run(tmp_path, "--json")
    assert result.returncode == 0
    report = _report(result)
    assert report["state"] == "current"
    assert report["changes"] == []


def test_default_command_is_the_openspec_cli() -> None:
    """The default command is the CLI the rest of the tooling pins."""
    module = _load_check()
    assert module.DEFAULT_COMMAND == "openspec"


def _load_check() -> object:
    """Import dev/check_generated_instructions.py without the dev package."""
    spec = importlib.util.spec_from_file_location("cgi", str(CHECK))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["cgi"] = module
    spec.loader.exec_module(module)
    return module
