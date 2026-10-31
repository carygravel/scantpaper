"""Sync the shared Debian packaging into a salsa checkout and draft the changelog.

Run from a salsa checkout after ``gbp import-orig``:

    python3 dev/sync_salsa.py --date 2026-11-01

Every file in ``packaging/debian`` is copied into ``debian``, files that the
previous release had but the new packaging does not are deleted, and
``debian/changelog`` is preserved. Anything else left in ``debian`` fails the
run: salsa owns only the changelog.

The entry is drafted from the difference between the newest ``debian/*`` tag
and the working tree. The tool prints the build, test, commit and upload
commands; it never commits, tags, signs or uploads.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Final, NoReturn

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

SOURCE_DIR: Final = "packaging/debian"
DEBIAN_DIR: Final = "debian"
CHANGELOG: Final = "changelog"
README: Final = "README.md"
NOT_SHARED: Final = frozenset({README, CHANGELOG})
DEPENDENCY_FIELDS: Final = (
    "Build-Depends",
    "Build-Depends-Indep",
    "Depends",
    "Recommends",
)
WEEKDAYS: Final = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS: Final = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)

_VERSION_RE = re.compile(r"(?m)^scantpaper \(([^)]+)\)")
_PACKAGER_RE = re.compile(r"(?m)^ -- (.+?)  \S")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SyncError(Exception):
    """Raised when the sync cannot produce a consistent tree."""


def _fail(message: str) -> NoReturn:
    """Raise a sync error with a message built by the caller."""
    raise SyncError(message)


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in ``root`` without raising."""
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=False,
        text=True,
    )


def _git_text(root: Path, *args: str) -> str:
    """Run git and return stripped standard output."""
    result = _run(root, *args)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        _fail(f"git {' '.join(args)} failed: {detail or 'unknown error'}")
    return result.stdout.strip()


def _git_bytes(root: Path, *args: str) -> bytes:
    """Run git and return raw standard output."""
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip()
        _fail(f"git {' '.join(args)} failed: {detail or 'unknown error'}")
    return result.stdout


def _files(directory: Path) -> set[str]:
    """Return the relative POSIX paths of every file below ``directory``."""
    return {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file()
    }


def _shared_paths(directory: Path) -> set[str]:
    """Return the relative paths of the shared packaging files."""
    return _files(directory) - NOT_SHARED


def _tag_shared_paths(root: Path, tag: str) -> set[str]:
    """Return the shared packaging paths recorded in ``tag``."""
    raw = _git_text(root, "ls-tree", "-r", "--name-only", tag, "--", SOURCE_DIR)
    prefix = f"{SOURCE_DIR}/"
    return {
        line[len(prefix) :] for line in raw.splitlines() if line.startswith(prefix)
    } - NOT_SHARED


def _tag_file(root: Path, tag: str, relative: str) -> bytes:
    """Return the content of a shared file as recorded in ``tag``."""
    return _git_bytes(root, "show", f"{tag}:{SOURCE_DIR}/{relative}")


def _read_upstream_version(root: Path) -> str:
    """Read the imported upstream version from pyproject.toml."""
    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
            "project"
        ]
    except (KeyError, OSError, TypeError, tomllib.TOMLDecodeError) as error:
        message = f"cannot read [project] from {root / 'pyproject.toml'}: {error}"
        raise SyncError(message) from error
    version = project.get("version")
    if not isinstance(version, str) or not version:
        _fail("pyproject.toml has no static project version")
    return version


def _newest_release_tag(root: Path) -> str:
    """Return the newest debian/<version> tag."""
    raw = _git_text(
        root,
        "for-each-ref",
        "--sort=-creatordate",
        "--format=%(refname:short)",
        "refs/tags/debian/*",
    )
    tags = [line for line in raw.splitlines() if line]
    if not tags:
        _fail("no previous debian/<version> tag; tag the released version first")
    return tags[0]


def _top_version(text: str) -> str:
    """Return the version of the newest changelog entry."""
    match = _VERSION_RE.search(text)
    if match is None:
        _fail("debian/changelog has no scantpaper entry")
    return str(match.group(1))


def _upstream_part(version: str) -> str:
    """Return the upstream part of a Debian version."""
    if "-" not in version:
        _fail(f"version {version} has no Debian revision")
    return version.rsplit("-", 1)[0]


def _revision_part(version: str) -> int:
    """Return the numeric Debian revision of a version."""
    try:
        return int(version.rsplit("-", 1)[1])
    except (IndexError, ValueError):
        _fail(f"version {version} has no numeric Debian revision")


def _packager(text: str) -> str:
    """Return the signer of the newest changelog entry."""
    match = _PACKAGER_RE.search(text)
    if match is None:
        _fail("debian/changelog has no signed-off entry")
    return str(match.group(1)).strip()


def _entry_date(args: argparse.Namespace) -> datetime.date:
    """Resolve the date for the drafted entry."""
    if args.date:
        if not _DATE_RE.match(args.date):
            _fail(f"--date must be YYYY-MM-DD: {args.date}")
        return datetime.date.fromisoformat(args.date)
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch is not None:
        try:
            moment = datetime.datetime.fromtimestamp(
                int(epoch), tz=datetime.timezone.utc
            )
        except (ValueError, OverflowError) as error:
            message = f"invalid SOURCE_DATE_EPOCH: {epoch}"
            raise SyncError(message) from error
        return moment.date()
    return datetime.datetime.now(tz=datetime.timezone.utc).date()


def _format_date(day: datetime.date) -> str:
    """Format a date for a Debian changelog trailer."""
    return (
        f"{WEEKDAYS[day.weekday()]}, {day.day:02d} "
        f"{MONTHS[day.month - 1]} {day.year} 00:00:00 +0000"
    )


def _dependencies(text: str) -> dict[str, tuple[str, ...]]:
    """Return the dependency items of the fields that matter for the draft."""
    fields: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if not line.strip():
            current = None
            continue
        if line[0] not in " \t" and ":" in line:
            name, _, value = line.partition(":")
            current = name.strip()
            if current in DEPENDENCY_FIELDS:
                fields.setdefault(current, []).extend(_items(value))
        elif current in DEPENDENCY_FIELDS:
            fields[current].extend(_items(line))
    return {name: tuple(items) for name, items in fields.items()}


def _items(value: str) -> list[str]:
    """Split a control field value into dependency items."""
    return [item.strip() for item in value.split(",") if item.strip()]


def _bullets(
    root: Path,
    tag: str,
    source: Path,
    new_paths: set[str],
    previous_paths: set[str],
) -> list[str]:
    """Describe the packaging difference between ``tag`` and the worktree."""
    added = sorted(new_paths - previous_paths)
    removed = sorted(previous_paths - new_paths)
    changed = sorted(
        path
        for path in new_paths & previous_paths
        if _tag_file(root, tag, path) != (source / path).read_bytes()
    )
    bullets = [f"debian/{path}: new" for path in added]
    bullets += [f"debian/{path}: removed" for path in removed]
    if "control" in changed:
        bullets += _dependency_bullets(
            _tag_file(root, tag, "control").decode(errors="replace"),
            (source / "control").read_text(encoding="utf-8"),
        )
    if "rules" in changed:
        bullets.append("debian/rules: updated")
    for path in changed:
        if path not in {"control", "rules"}:
            bullets.append(f"debian/{path}: updated")
    return bullets


def _dependency_bullets(before: str, after: str) -> list[str]:
    """Describe added and removed dependency items per field."""
    old = _dependencies(before)
    new = _dependencies(after)
    bullets = []
    for field in DEPENDENCY_FIELDS:
        added = sorted(set(new.get(field, ())) - set(old.get(field, ())))
        removed = sorted(set(old.get(field, ())) - set(new.get(field, ())))
        if added or removed:
            items = [f"+{item}" for item in added] + [f"-{item}" for item in removed]
            bullets.append(f"{field}: {', '.join(items)}")
    return bullets


def _entry(
    version: str,
    headline: str,
    bullets: list[str],
    packager: str,
    date: datetime.date,
) -> str:
    """Build the changelog entry."""
    lines = [
        f"scantpaper ({version}) unstable; urgency=medium",
        "",
        f"  * {headline}",
    ]
    lines += [f"    {bullet}" for bullet in bullets]
    lines += ["", f" -- {packager}  {_format_date(date)}"]
    return "\n".join(lines) + "\n"


def _insert_entry(changelog: str, entry: str, version: str) -> str:
    """Prepend the entry, replacing it when a draft of it is already on top."""
    matches = list(_VERSION_RE.finditer(changelog))
    if matches and matches[0].group(1) == version:
        tail = changelog[matches[1].start() :] if len(matches) > 1 else ""
        return entry + ("\n" + tail if tail else "")
    return entry + "\n" + changelog


def _prune(directory: Path, stop: Path) -> None:
    """Remove empty directories up to ``stop``."""
    while directory != stop and directory.is_dir() and not any(directory.iterdir()):
        directory.rmdir()
        directory = directory.parent


def _checkout(args: argparse.Namespace) -> tuple[Path, str]:
    """Validate the checkout and return its root and upstream version."""
    root = Path(str(args.root)).resolve()
    branch = str(args.debian_branch)
    if not (root / DEBIAN_DIR / CHANGELOG).is_file():
        _fail(f"no {DEBIAN_DIR}/{CHANGELOG}; this is not a salsa checkout")
    if not (root / SOURCE_DIR).is_dir():
        _fail(f"no {SOURCE_DIR}; check out the imported upstream tree first")
    if not (root / "pyproject.toml").is_file():
        _fail("no pyproject.toml; check out the imported upstream tree first")
    inside = _run(root, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        _fail(f"{root} is not a git worktree")
    current = _git_text(root, "symbolic-ref", "--short", "HEAD")
    if current != branch:
        _fail(f"on branch {current!r}, expected {branch!r}")
    version = _read_upstream_version(root)
    if not _git_text(root, "tag", "--list", f"upstream/{version}"):
        _fail(f"upstream/{version} tag not found; run gbp import-orig first")
    return root, version


def _prepare(args: argparse.Namespace) -> tuple[str, str, list[str], str]:
    """Validate the checkout and return the version, tag, bullets and entry."""
    root, version = _checkout(args)

    tag = _newest_release_tag(root)
    old_version = tag.removeprefix("debian/")
    if old_version == tag:
        _fail(f"release tag {tag} has an unexpected name")
    previous_paths = _tag_shared_paths(root, tag)
    new_paths = _shared_paths(root / SOURCE_DIR)
    if not previous_paths:
        leftovers = _files(root / DEBIAN_DIR) - {CHANGELOG}
        if leftovers:
            names = ", ".join(f"debian/{path}" for path in sorted(leftovers))
            _fail(
                f"the previous release has no packaging/debian (pre-migration); "
                f"remove everything under debian/ except the changelog once, "
                f"then rerun: {names}"
            )

    expected = set(_files(root / DEBIAN_DIR))
    allowed = new_paths | {CHANGELOG} | (previous_paths - new_paths)
    extras = sorted(expected - allowed)
    if extras:
        names = ", ".join(f"debian/{path}" for path in extras)
        _fail(f"unexpected file(s) in debian/: {names}; salsa owns only the changelog")

    changelog_text = (root / DEBIAN_DIR / CHANGELOG).read_text(encoding="utf-8")
    packager = _packager(changelog_text)
    old_upstream = _upstream_part(old_version)
    if version != old_upstream:
        revision = 1
        headline = "New upstream release."
    else:
        revision = _revision_part(old_version) + 1
        headline = "Debian packaging update."
    new_version = f"{version}-{revision}"
    bullets = (
        _bullets(root, tag, root / SOURCE_DIR, new_paths, previous_paths)
        if previous_paths
        else []
    )
    entry = _entry(new_version, headline, bullets, packager, _entry_date(args))
    return new_version, tag, bullets, entry


def _sync(args: argparse.Namespace) -> None:
    """Perform the sync and print the next steps."""
    root = args.root.resolve()
    new_version, tag, bullets, entry = _prepare(args)
    source = root / SOURCE_DIR
    target = root / DEBIAN_DIR
    previous_paths = _tag_shared_paths(root, tag)
    new_paths = _shared_paths(source)
    removed = sorted(previous_paths - new_paths)

    if args.dry_run:
        print(f"Would sync {len(new_paths)} file(s) from {SOURCE_DIR} to {DEBIAN_DIR}")
        if removed:
            print("Would remove: " + ", ".join(f"debian/{path}" for path in removed))
        print(f"Would draft debian/changelog entry {new_version}")
        print()
        print(entry, end="")
        _print_commands(new_version)
        return

    for path in removed:
        stale = target / path
        if stale.exists():
            stale.unlink()
            _prune(stale.parent, target)
    for path in sorted(new_paths):
        destination = target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / path, destination)

    pending = _files(target) - new_paths - {CHANGELOG}
    if pending:
        names = ", ".join(f"debian/{path}" for path in sorted(pending))
        _fail(f"unexpected file(s) remain in debian/: {names}")

    changelog_path = target / CHANGELOG
    changelog = changelog_path.read_text(encoding="utf-8")
    changelog_path.write_text(
        _insert_entry(changelog, entry, new_version), encoding="utf-8"
    )

    print(f"Synced {len(new_paths)} file(s), removed {len(removed)}")
    print(f"Drafted debian/changelog entry {new_version} ({len(bullets)} bullet(s))")
    print()
    print(entry, end="")
    _print_commands(new_version)


def _print_commands(version: str) -> None:
    """Print the commands the maintainer runs next."""
    changes = f"../scantpaper_{version}_source.changes"
    print("Next steps:")
    for command in (
        "debuild -S -sa",
        f"lintian -iI --pedantic {changes}",
        f"autopkgtest {changes} -- unshare --release sid",
        "debcommit -r",
        (
            "git push --set-upstream git@salsa.debian.org:python-team/packages/"
            "scantpaper.git : --tags"
        ),
        f"dput ftp-master {changes}",
    ):
        print(f"  {command}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="salsa checkout (default: current directory)",
    )
    parser.add_argument(
        "--debian-branch",
        default="debian/master",
        help="branch the checkout must be on (default: debian/master)",
    )
    parser.add_argument(
        "--date",
        help="entry date as YYYY-MM-DD (default: SOURCE_DATE_EPOCH or today, "
        "midnight UTC)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the planned changes and the entry without writing",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the sync, returning a process exit status."""
    args = parse_args(argv)
    try:
        _sync(args)
    except SyncError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
