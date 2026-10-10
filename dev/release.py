"""Prepare the release version files for a release.

The tool updates the release version in ``pyproject.toml``, dates the newest
``(unreleased)`` section in ``changelog.md``, and adds a matching ``<release>``
element to ``org.scantpaper.desktop.metainfo.xml``. A single resolved release
date is written to both the changelog and the metainfo file, so the two can
never drift apart.

It does not touch version control and does not regenerate the translation
template: committing, tagging, pushing and ``dev/generate_pot.py`` remain
separate manual steps (see ``release_procedure.md``).

Usage:
    python3 dev/release.py [--version X.Y.Z] [--date YYYY-MM-DD]
        [--dry-run] [--root DIR]
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import os
import re
import sys
from pathlib import Path
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[1]

CHANGELOG = "changelog.md"
PYPROJECT = "pyproject.toml"
METAINFO = "org.scantpaper.desktop.metainfo.xml"

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_UNRELEASED_RE = re.compile(r"(?m)^##[ \t]+(\S+)[ \t]+\(unreleased\)[ \t]*$")


class ReleaseError(Exception):
    """A release-preparation error whose message is safe to show the user."""


def resolve_version(changelog: str, override: str | None = None) -> str:
    """Return the release version from the changelog's (unreleased) heading."""
    versions = [match.group(1) for match in _UNRELEASED_RE.finditer(changelog)]
    if len(versions) != 1:
        message = (
            f"expected exactly one '(unreleased)' heading in {CHANGELOG}, "
            f"found {len(versions)}"
        )
        raise ReleaseError(message)
    version = cast("str", versions[0])
    if override is not None and override != version:
        message = (
            f"--version {override} does not match the {CHANGELOG} heading {version}"
        )
        raise ReleaseError(message)
    return version


def resolve_date(
    date_override: str | None,
    source_date_epoch: str | None,
    now: datetime.datetime,
) -> str:
    """Resolve the single release date shared by every written file."""
    if date_override is not None:
        if not _DATE_RE.fullmatch(date_override):
            message = f"--date must be YYYY-MM-DD, got {date_override!r}"
            raise ReleaseError(message)
        return date_override
    if source_date_epoch is not None:
        try:
            epoch = int(source_date_epoch)
        except ValueError as error:
            message = f"invalid SOURCE_DATE_EPOCH {source_date_epoch!r}"
            raise ReleaseError(message) from error
        stamp = datetime.datetime.fromtimestamp(epoch, tz=datetime.timezone.utc)
        return stamp.strftime("%Y-%m-%d")
    return now.astimezone().strftime("%Y-%m-%d")


def stamp_changelog(changelog: str, version: str, date: str) -> str:
    """Replace the release version's (unreleased) marker with ``date``."""
    pattern = re.compile(
        rf"(?m)^##[ \t]+{re.escape(version)}[ \t]+\(unreleased\)[ \t]*$"
    )
    stamped, count = pattern.subn(f"## {version} ({date})", changelog)
    if count != 1:
        message = (
            f"expected one '## {version} (unreleased)' heading in "
            f"{CHANGELOG}, found {count}"
        )
        raise ReleaseError(message)
    return stamped


def bump_pyproject(pyproject: str, version: str) -> str:
    """Set ``[project] version`` in ``pyproject.toml`` to ``version``."""
    lines = pyproject.splitlines(keepends=True)
    start, end = _project_table_bounds(lines)
    pattern = re.compile(r'^version\s*=\s*"[^"]*"')
    for index in range(start, end):
        match = pattern.match(lines[index])
        if match:
            lines[index] = f'version = "{version}"' + lines[index][match.end() :]
            return "".join(lines)
    message = f"{PYPROJECT}: no 'version' key in the [project] table"
    raise ReleaseError(message)


def add_metainfo_release(metainfo: str, version: str, date: str) -> str:
    """Insert the new release as the first child of ``<releases>``."""
    pattern = re.compile(r"(?m)^(?P<indent>[ \t]*)<releases>[ \t]*$")
    match = pattern.search(metainfo)
    if match is None:
        message = f"{METAINFO}: no <releases> element"
        raise ReleaseError(message)
    indent = match.group("indent") + "  "
    entry = f'{indent}<release version="{version}" date="{date}" />'
    insert_at = match.end()
    return f"{metainfo[:insert_at]}\n{entry}{metainfo[insert_at:]}"


def prepare(
    root: Path,
    *,
    version: str | None,
    date: str | None,
    source_date_epoch: str | None,
    now: datetime.datetime,
) -> tuple[str, str, dict[Path, tuple[str, str]]]:
    """Compute every change in memory; return (version, date, updates).

    No file is written here, so a failure in any transformation leaves the
    real files untouched (all-or-nothing).
    """
    changelog_path = root / CHANGELOG
    pyproject_path = root / PYPROJECT
    metainfo_path = root / METAINFO

    changelog = _read(changelog_path)
    pyproject = _read(pyproject_path)
    metainfo = _read(metainfo_path)

    resolved_version = resolve_version(changelog, version)
    resolved_date = resolve_date(date, source_date_epoch, now)

    updates = {
        changelog_path: (
            changelog,
            stamp_changelog(changelog, resolved_version, resolved_date),
        ),
        pyproject_path: (
            pyproject,
            bump_pyproject(pyproject, resolved_version),
        ),
        metainfo_path: (
            metainfo,
            add_metainfo_release(metainfo, resolved_version, resolved_date),
        ),
    }
    return resolved_version, resolved_date, updates


def main() -> int:
    """Run the release-preparation entry point."""
    parser = argparse.ArgumentParser(
        description="Prepare the release version files for a release"
    )
    parser.add_argument(
        "--version",
        help="Release version; must match the changelog's (unreleased) heading",
    )
    parser.add_argument(
        "--date",
        help="Release date as YYYY-MM-DD (default: today, or SOURCE_DATE_EPOCH)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing any file",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root containing the version files (default: repo root)",
    )
    args = parser.parse_args()

    try:
        version, date, updates = prepare(
            args.root,
            version=args.version,
            date=args.date,
            source_date_epoch=os.environ.get("SOURCE_DATE_EPOCH"),
            now=datetime.datetime.now(tz=datetime.timezone.utc).astimezone(),
        )
    except ReleaseError as error:
        print(f"[FAIL] {error}")
        return 1

    for path, (old, new) in updates.items():
        if old != new:
            sys.stdout.write(_diff(path.name, old, new))

    if args.dry_run:
        print(f"Dry run: would prepare release {version} dated {date}.")
        return 0

    for path, (_old, new) in updates.items():
        path.write_text(new, encoding="utf-8")
        print(f"Updated {path.name}")
    print(f"Prepared release {version} dated {date}.")
    return 0


def _project_table_bounds(lines: list[str]) -> tuple[int, int]:
    """Return the [start, end) line range of the ``[project]`` table."""
    start = None
    for index, line in enumerate(lines):
        if line.strip() == "[project]":
            start = index
            break
    if start is None:
        message = f"{PYPROJECT}: no [project] table"
        raise ReleaseError(message)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            return start, index
    return start, len(lines)


def _read(path: Path) -> str:
    """Read ``path`` as UTF-8, converting OS errors into a ReleaseError."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        message = f"cannot read {path}: {error}"
        raise ReleaseError(message) from error


def _diff(name: str, old: str, new: str) -> str:
    """Return a unified diff of ``old`` and ``new`` labelled with ``name``."""
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=name,
            tofile=name,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
