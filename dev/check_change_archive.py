"""Fail when a completed OpenSpec change is still waiting to be archived.

``openspec list --json`` reports a change as ``complete`` only when every task
is ticked, so a complete change that is still under ``openspec/changes/`` is
one nobody archived: the code it describes can ship while its delta never
reaches ``openspec/specs/``. CI runs this gate so that cannot happen without a
red build.

The gate reads the CLI's own status rather than parsing ``tasks.md``, so the
definition of "complete" stays OpenSpec's. ``no-tasks`` is deliberately not
complete, which keeps a freshly scaffolded change pushable.

Exit codes: 0 when nothing is waiting to be archived, 1 when a completed
change is still active, and 2 when the state cannot be read - so "could not
tell" is never reported as "clean".
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_COMMAND = "openspec"
LIST_TIMEOUT = 120

COMPLETE = "complete"
CLEAN = "clean"
UNARCHIVED = "unarchived"


class CheckError(Exception):
    """Raised when the change list cannot be read."""


@dataclass(frozen=True)
class Change:
    """One change as ``openspec list --json`` describes it."""

    name: str
    status: str


def read_changes(command: str, cwd: Path) -> list[Change]:
    """Return the changes the CLI reports for the project at ``cwd``."""
    try:
        completed = subprocess.run(
            [command, "list", "--json"],
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
            timeout=LIST_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as error:
        message = f"cannot run {command!r}: {error}"
        raise CheckError(message) from error
    if completed.returncode != 0:
        output = (completed.stdout + completed.stderr).strip()
        message = f"{command} list --json exited {completed.returncode}: {output}"
        raise CheckError(message)
    try:
        payload = json.loads(completed.stdout)
    except ValueError as error:
        message = f"{command} list --json did not return JSON: {error}"
        raise CheckError(message) from error
    if not isinstance(payload, dict):
        message = (
            f"{command} list --json returned {type(payload).__name__}, not an object"
        )
        raise CheckError(message)
    entries = payload.get("changes")
    if not isinstance(entries, list):
        message = f"{command} list --json returned no 'changes' list"
        raise CheckError(message)
    changes = []
    for entry in entries:
        if not isinstance(entry, dict):
            message = f"{command} list --json returned a non-object change entry"
            raise CheckError(message)
        name = entry.get("name")
        status = entry.get("status")
        if not isinstance(name, str) or not isinstance(status, str):
            message = f"{command} list --json returned a change without name and status"
            raise CheckError(message)
        changes.append(Change(name, status))
    return changes


def unarchived(changes: list[Change]) -> list[str]:
    """Return the names of completed changes that are still active."""
    return [change.name for change in changes if change.status == COMPLETE]


def _summary(names: list[str]) -> str:
    """Render the result for a human reading a terminal."""
    if not names:
        return "OpenSpec changes: nothing is waiting to be archived"
    lines = ["OpenSpec changes: completed but still under openspec/changes/"]
    lines.extend(f"  - {name}" for name in names)
    lines.append("Archive each one in the commit that ticks its last task:")
    lines.extend(f"  openspec archive {name}" for name in names)
    return "\n".join(lines)


def build_report(names: list[str]) -> dict[str, object]:
    """Assemble the report the workflow can consume as JSON."""
    return {
        "state": UNARCHIVED if names else CLEAN,
        "changes": names,
        "summary": _summary(names),
    }


def main() -> int:
    """Fail when a completed change is still active."""
    parser = argparse.ArgumentParser(
        description="Fail when a completed OpenSpec change is not archived"
    )
    parser.add_argument(
        "--openspec",
        default=DEFAULT_COMMAND,
        help=f"OpenSpec CLI to run (default: {DEFAULT_COMMAND})",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=Path(),
        help="Directory the CLI runs in (default: the current)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON, for the workflow to consume",
    )
    args = parser.parse_args()

    try:
        names = unarchived(read_changes(args.openspec, args.cwd))
    except CheckError as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 2

    report = build_report(names)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(report["summary"])
    return 1 if names else 0


if __name__ == "__main__":
    sys.exit(main())
