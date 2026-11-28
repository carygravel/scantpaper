"""Fail when the generated instruction files are behind the pinned CLI.

``openspec update`` rewrites the agent instruction files from the installed
CLI. CI installs the version recorded in ``dev/openspec-version``, so a pin that
is bumped without regenerating those files leaves the repository's copies
behind the CLI it installs - which is how the files here stayed at 1.10.0 while
the pin moved to 2.2.0.

The gate asks the CLI what it would change and fails when any of it lands
inside the repository. Paths outside it - the CLI's own configuration, which
lives in the user's home directory - are ignored, because a clean checkout has
no such file and the gate must not fail for that.

Exit codes: 0 when the generated files are current, 1 when regenerating them
would change a repository file, and 2 when the plan cannot be read - so
"could not tell" is never reported as "current".
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_COMMAND = "openspec"
PLAN_TIMEOUT = 120

CURRENT = "current"
STALE = "stale"


class CheckError(Exception):
    """Raised when the plan cannot be read."""


@dataclass(frozen=True)
class PlannedChange:
    """One file the CLI would write."""

    path: str
    action: str


def read_plan(command: str, root: Path) -> list[PlannedChange]:
    """Return every file the CLI would change, inside the repository or not."""
    try:
        completed = subprocess.run(
            [command, "update", "--dry-run", "--json"],
            capture_output=True,
            text=True,
            check=False,
            cwd=root,
            timeout=PLAN_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as error:
        message = f"cannot run {command!r}: {error}"
        raise CheckError(message) from error
    if completed.returncode != 0:
        output = (completed.stdout + completed.stderr).strip()
        message = f"{command} update --dry-run exited {completed.returncode}: {output}"
        raise CheckError(message)
    try:
        payload = json.loads(completed.stdout)
    except ValueError as error:
        message = f"{command} update --dry-run did not return JSON: {error}"
        raise CheckError(message) from error
    if not isinstance(payload, dict):
        message = f"{command} update --dry-run returned {type(payload).__name__}"
        raise CheckError(message)
    failures = payload.get("failures")
    if isinstance(failures, list) and failures:
        message = f"{command} update --dry-run reported failures: {failures!r}"
        raise CheckError(message)
    entries = payload.get("changes")
    if not isinstance(entries, list):
        message = f"{command} update --dry-run returned no 'changes' list"
        raise CheckError(message)
    changes = []
    for entry in entries:
        if not isinstance(entry, dict):
            message = "update --dry-run returned a non-object change entry"
            raise CheckError(message)
        path = entry.get("path")
        action = entry.get("action")
        if not isinstance(path, str) or not isinstance(action, str):
            message = "update --dry-run returned a change without path and action"
            raise CheckError(message)
        changes.append(PlannedChange(path, action))
    return changes


def in_repository(root: Path, changes: list[PlannedChange]) -> list[PlannedChange]:
    """Return the changes that land inside ``root``.

    A relative path is resolved against ``root`` rather than the process
    working directory, because the CLI runs with ``root`` as its cwd. Absolute
    paths are compared as they are.
    """
    resolved_root = root.resolve()
    inside = []
    for change in changes:
        path = Path(change.path)
        if not path.is_absolute():
            path = resolved_root / path
        if path.resolve().is_relative_to(resolved_root):
            inside.append(change)
    return inside


def _summary(changes: list[PlannedChange]) -> str:
    """Render the result for a human reading a terminal."""
    if not changes:
        return "Generated OpenSpec instruction files: current"
    lines = [
        "Generated OpenSpec instruction files are behind the pinned CLI:",
    ]
    lines.extend(f"  {change.action} {change.path}" for change in changes)
    lines.append("Run `openspec update` and commit the result.")
    return "\n".join(lines)


def build_report(changes: list[PlannedChange]) -> dict[str, object]:
    """Assemble the report the workflow can consume as JSON."""
    return {
        "state": STALE if changes else CURRENT,
        "changes": [
            {"path": change.path, "action": change.action} for change in changes
        ],
        "summary": _summary(changes),
    }


def main() -> int:
    """Fail when regenerating the instruction files would change the repository."""
    parser = argparse.ArgumentParser(
        description=(
            "Fail when the generated OpenSpec instruction files are behind "
            "the pinned CLI"
        )
    )
    parser.add_argument(
        "--openspec",
        default=DEFAULT_COMMAND,
        help=f"OpenSpec CLI to run (default: {DEFAULT_COMMAND})",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(),
        help="Repository root the CLI runs in (default: the current directory)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON, for the workflow to consume",
    )
    args = parser.parse_args()

    try:
        changes = in_repository(args.root, read_plan(args.openspec, args.root))
    except CheckError as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 2

    report = build_report(changes)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(report["summary"])
    return 1 if changes else 0


if __name__ == "__main__":
    sys.exit(main())
