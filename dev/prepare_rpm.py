"""Render an RPM spec and source archive from a git revision.

The spec templates in ``packaging`` are not valid RPM specs on their own:
``@VERSION@``, ``@RELEASE@`` and ``@CHANGELOG@`` are filled in here from a
specific source revision.  The source archive is produced with ``git
archive`` so local builds and CI package exactly the same tree.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, NoReturn

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

PLACEHOLDERS: Final = ("@VERSION@", "@RELEASE@", "@CHANGELOG@")
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
CHANGELOG_ENTRY = re.compile(
    r"^[*-] (?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) "
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"\d{1,2} \d{4} (?P<packager>.+?) - (?P<evr>\S+)\s*$",
    re.MULTILINE,
)


class PrepareError(Exception):
    """Raised when the renderer cannot create consistent outputs."""


def _fail(message: str) -> NoReturn:
    """Raise a renderer error with a message built by the caller."""
    raise PrepareError(message)


@dataclass(frozen=True)
class Source:
    """Metadata read from the selected source revision."""

    version: str
    release: str
    short_sha: str
    timestamp: int
    is_release: bool


def _git_text(repo_root: Path, *args: str) -> str:
    """Run git and return stripped standard output."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        _fail(f"git {' '.join(args)} failed: {detail or 'unknown error'}")
    return result.stdout.strip()


def _git_bytes(repo_root: Path, *args: str) -> bytes:
    """Run git and return raw standard output."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip()
        _fail(f"git {' '.join(args)} failed: {detail or 'unknown error'}")
    return result.stdout


def _read_version(repo_root: Path, source_ref: str) -> str:
    """Read the project version from pyproject.toml at the source ref."""
    raw = _git_bytes(repo_root, "show", f"{source_ref}:pyproject.toml")
    try:
        project = tomllib.loads(raw.decode("utf-8"))["project"]
    except (KeyError, TypeError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        message = f"cannot read [project] metadata from {source_ref}:pyproject.toml"
        raise PrepareError(message) from error
    if not isinstance(project, dict):
        _fail(f"{source_ref}:pyproject.toml has no [project] table")
    version = project.get("version")
    if not isinstance(version, str) or not version:
        _fail(f"{source_ref}:pyproject.toml has no static project version")
    return version


def _tags_at(repo_root: Path, source_ref: str) -> list[str]:
    """Return the tags pointing at the source revision."""
    return _git_text(repo_root, "tag", "--points-at", source_ref).splitlines()


def _check_tag(repo_root: Path, source_ref: str, version: str) -> None:
    """Reject tags that disagree with the version in pyproject.toml."""
    for tag in _tags_at(repo_root, source_ref):
        if tag.startswith("v") and tag[1:] != version:
            _fail(f"tag {tag} does not match pyproject version {version}")


def _source_metadata(repo_root: Path, source_ref: str, version: str) -> Source:
    """Collect release metadata for the selected revision."""
    if _git_text(repo_root, "rev-parse", "--is-shallow-repository") == "true":
        _fail(
            "repository is shallow; fetch full history so the commit count is correct"
        )
    _check_tag(repo_root, source_ref, version)
    try:
        count = int(_git_text(repo_root, "rev-list", "--count", source_ref))
        timestamp = int(_git_text(repo_root, "show", "-s", "--format=%ct", source_ref))
    except ValueError as error:
        message = f"cannot read commit metadata for {source_ref}"
        raise PrepareError(message) from error
    short_sha = _git_text(repo_root, "rev-parse", "--short", source_ref)
    is_release = f"v{version}" in _tags_at(repo_root, source_ref)
    return Source(
        version=version,
        release=f"0.{count}.g{short_sha}",
        short_sha=short_sha,
        timestamp=timestamp,
        is_release=is_release,
    )


def _read_template(path: Path) -> str:
    """Read a template and require every substitution marker."""
    try:
        template = path.read_text(encoding="utf-8")
    except OSError as error:
        message = f"cannot read template {path}: {error}"
        raise PrepareError(message) from error
    missing = [
        placeholder for placeholder in PLACEHOLDERS if placeholder not in template
    ]
    if missing:
        _fail(f"template {path} is missing placeholder(s): {', '.join(missing)}")
    return template


def _packager(template: str) -> str:
    """Reuse the newest historical changelog entry's packager."""
    match = CHANGELOG_ENTRY.search(template)
    if match is None:
        _fail("template has no historical changelog entry with a packager")
    packager = str(match.group("packager")).strip()
    if not packager:
        _fail("template has no historical changelog entry with a packager")
    return packager


def _format_date(timestamp: int) -> str:
    """Format a UTC timestamp with English RPM changelog abbreviations."""
    moment = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return (
        f"{WEEKDAYS[moment.weekday()]} {MONTHS[moment.month - 1]} "
        f"{moment.day:02d} {moment.year}"
    )


def _changelog(source: Source, packager: str) -> str:
    """Build the new changelog entry for this build."""
    header = (
        f"* {_format_date(source.timestamp)} {packager} - "
        f"{source.version}-{source.release}"
    )
    if source.is_release:
        message = f"- Release {source.version}."
    else:
        message = f"- Snapshot build from commit {source.short_sha}."
    return f"{header}\n{message}"


def _render(template: str, changelog: str, source: Source) -> str:
    """Substitute the template markers and validate the result."""
    rendered = (
        template.replace("@VERSION@", source.version)
        .replace("@RELEASE@", source.release)
        .replace("@CHANGELOG@", changelog)
    )
    leftovers = [placeholder for placeholder in PLACEHOLDERS if placeholder in rendered]
    if leftovers:
        _fail(f"rendered spec still contains placeholder(s): {', '.join(leftovers)}")
    if re.search(r"^Epoch:", rendered, re.MULTILINE):
        _fail("template must not set Epoch")
    return rendered


def _write_archive(
    repo_root: Path, source_ref: str, version: str, destination: Path
) -> Path:
    """Write a git archive for the source ref to a temporary file."""
    expected_name = f"scantpaper-{version}.tar.gz"
    if destination.name != expected_name:
        _fail(f"source archive must be named {expected_name}: {destination.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "archive",
                    "--format=tar.gz",
                    f"--prefix=scantpaper-{version}/",
                    source_ref,
                ],
                capture_output=False,
                check=False,
                stderr=subprocess.PIPE,
                stdout=stream,
            )
        except OSError as error:
            temporary.unlink(missing_ok=True)
            message = f"cannot run git archive for {source_ref}: {error}"
            raise PrepareError(message) from error
    if result.returncode != 0:
        temporary.unlink(missing_ok=True)
        detail = result.stderr.decode(errors="replace").strip()
        _fail(f"git archive failed for {source_ref}: {detail or 'unknown error'}")
    return temporary


def _write_spec(destination: Path, contents: str) -> Path:
    """Write rendered spec text to a temporary file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(contents)
        except OSError as error:
            stream.close()
            temporary.unlink(missing_ok=True)
            message = f"cannot write spec {destination}: {error}"
            raise PrepareError(message) from error
    return temporary


def prepare(
    *,
    repo_root: Path,
    template: Path,
    source_ref: str,
    spec_out: Path,
    sources_dir: Path,
) -> None:
    """Render the spec and archive for a source ref."""
    if not repo_root.is_dir():
        _fail(f"repository root does not exist: {repo_root}")
    version = _read_version(repo_root, source_ref)
    source = _source_metadata(repo_root, source_ref, version)
    template_text = _read_template(template)
    changelog = _changelog(source, _packager(template_text))
    rendered = _render(template_text, changelog, source)
    archive = sources_dir / f"scantpaper-{version}.tar.gz"

    temporary_archive: Path | None = None
    temporary_spec: Path | None = None
    try:
        temporary_archive = _write_archive(repo_root, source_ref, version, archive)
        temporary_spec = _write_spec(spec_out, rendered)
        temporary_archive.replace(archive)
        temporary_archive = None
        temporary_spec.replace(spec_out)
        temporary_spec = None
    finally:
        if temporary_archive is not None:
            temporary_archive.unlink(missing_ok=True)
        if temporary_spec is not None:
            temporary_spec.unlink(missing_ok=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template",
        type=Path,
        required=True,
        help="path to the template spec in the working tree",
    )
    parser.add_argument(
        "--source-ref",
        required=True,
        help="git revision whose metadata and source tree are packaged",
    )
    parser.add_argument(
        "--spec-out",
        type=Path,
        required=True,
        help="path for the rendered spec",
    )
    parser.add_argument(
        "--sources-dir",
        type=Path,
        required=True,
        help="directory for the generated source archive",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="git working tree root (default: current directory)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Render the spec and archive, returning a process exit status."""
    args = parse_args(argv)
    try:
        prepare(
            repo_root=args.repo_root,
            template=args.template,
            source_ref=args.source_ref,
            spec_out=args.spec_out,
            sources_dir=args.sources_dir,
        )
    except PrepareError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
