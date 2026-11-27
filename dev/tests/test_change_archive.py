"""Tests for the OpenSpec archive gate dev/check_change_archive.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import TypedDict, cast

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CHECK = REPO_ROOT / "dev" / "check_change_archive.py"


class ReportJson(TypedDict):
    """The JSON report the gate emits with --json."""

    state: str
    changes: list[str]
    summary: str


def _changes(*entries: tuple[str, str]) -> dict[str, object]:
    """Build an ``openspec list --json`` document from name/status pairs."""
    return {"changes": [{"name": name, "status": status} for name, status in entries]}


def _stub(tmp_path: Path, payload: object) -> Path:
    """Write an executable that prints ``payload`` as JSON."""
    path = tmp_path / "openspec-stub"
    script = f"#!/usr/bin/env python3\nimport json\nprint(json.dumps({payload!r}))\n"
    path.write_text(script, encoding="utf-8")
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
    tmp_path: Path, *flags: str, openspec: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the gate against a stub CLI in ``tmp_path``."""
    args = [
        sys.executable,
        str(CHECK),
        "--openspec",
        str(openspec or _stub(tmp_path, _changes())),
        "--cwd",
        str(tmp_path),
    ]
    args += list(flags)
    return subprocess.run(args, capture_output=True, text=True, check=False)


def _report(result: subprocess.CompletedProcess[str]) -> ReportJson:
    """Return the --json report as a typed dict."""
    return cast("ReportJson", json.loads(result.stdout))


def test_completed_change_fails_the_gate(tmp_path: Path) -> None:
    """A change with every task ticked must not stay active."""
    stub = _stub(tmp_path, _changes(("finish-me", "complete")))
    result = _run(tmp_path, openspec=stub)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "finish-me" in result.stdout
    assert "openspec archive finish-me" in result.stdout


def test_several_completed_changes_are_all_named(tmp_path: Path) -> None:
    """Every offending change appears in the failure, not just the first."""
    stub = _stub(
        tmp_path,
        _changes(
            ("first", "complete"), ("second", "complete"), ("third", "in-progress")
        ),
    )
    result = _run(tmp_path, openspec=stub)
    assert result.returncode == 1
    assert "first" in result.stdout
    assert "second" in result.stdout
    assert "third" not in result.stdout


def test_in_progress_change_is_allowed(tmp_path: Path) -> None:
    """An unticked task keeps a change legitimately active."""
    stub = _stub(tmp_path, _changes(("work-in-progress", "in-progress")))
    result = _run(tmp_path, openspec=stub)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "nothing is waiting" in result.stdout


def test_change_with_no_tasks_is_allowed(tmp_path: Path) -> None:
    """A freshly scaffolded change is not a completed one."""
    stub = _stub(tmp_path, _changes(("just-created", "no-tasks")))
    result = _run(tmp_path, openspec=stub)
    assert result.returncode == 0


def test_empty_change_list_is_allowed(tmp_path: Path) -> None:
    """A repository with no active change passes the gate."""
    result = _run(tmp_path)
    assert result.returncode == 0


def test_unreadable_cli_fails_loudly(tmp_path: Path) -> None:
    """A CLI that cannot list changes is not reported as clean."""
    result = _run(tmp_path, openspec=_failing_stub(tmp_path))
    assert result.returncode == 2
    assert "[FAIL]" in result.stderr


def test_missing_cli_fails_loudly(tmp_path: Path) -> None:
    """A CLI that is not installed is not reported as clean."""
    result = _run(tmp_path, openspec=tmp_path / "definitely-not-openspec")
    assert result.returncode == 2
    assert "[FAIL]" in result.stderr


def test_invalid_json_fails_loudly(tmp_path: Path) -> None:
    """Output that is not JSON is not reported as clean."""
    stub = tmp_path / "openspec-bad-json"
    stub.write_text("#!/usr/bin/env python3\nprint('not json')\n", encoding="utf-8")
    stub.chmod(0o755)
    result = _run(tmp_path, openspec=stub)
    assert result.returncode == 2
    assert "[FAIL]" in result.stderr


def test_json_report_names_the_completed_changes(tmp_path: Path) -> None:
    """The machine-readable report carries the state and the names."""
    stub = _stub(tmp_path, _changes(("a", "complete"), ("b", "complete")))
    result = _run(tmp_path, "--json", openspec=stub)
    assert result.returncode == 1
    report = _report(result)
    assert report["state"] == "unarchived"
    assert report["changes"] == ["a", "b"]
    assert "a" in report["summary"]


def test_json_report_is_clean_when_nothing_is_complete(tmp_path: Path) -> None:
    """A clean tree reports a clean state."""
    stub = _stub(tmp_path, _changes(("a", "in-progress")))
    result = _run(tmp_path, "--json", openspec=stub)
    assert result.returncode == 0
    report = _report(result)
    assert report["state"] == "clean"
    assert report["changes"] == []


def test_default_command_is_the_openspec_cli() -> None:
    """The default command is the CLI the rest of the tooling pins."""
    module = _load_check()
    assert module.DEFAULT_COMMAND == "openspec"


def _load_check() -> object:
    """Import dev/check_change_archive.py directly, bypassing the dev package."""
    spec = importlib.util.spec_from_file_location("cca", str(CHECK))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["cca"] = module
    spec.loader.exec_module(module)
    return module
