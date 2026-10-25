"""Render the Debian packaging and source tree from a git revision.

``packaging/debian`` is a template, not a buildable Debian source package: its
changelog carries placeholders, and ``debian/`` has to sit at the root of the
tree being built.  This renderer materialises the selected git revision under
``build/deb/`` and renders the packaging into it, so no ``debian`` directory is
created in the repository itself.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, NoReturn

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

PLACEHOLDERS: Final = ("@VERSION@", "@DATE@", "@TEXT@")
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
README: Final = "README.md"


class PrepareError(Exception):
    """Raised when the renderer cannot create a consistent build tree."""


def _fail(message: str) -> NoReturn:
    """Raise a renderer error with a message built by the caller."""
    raise PrepareError(message)


@dataclass(frozen=True)
class Source:
    """Metadata read from the selected source revision."""

    version: str
    debian_version: str
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


def _format_date(timestamp: int) -> str:
    """Format a UTC timestamp for a Debian changelog entry."""
    moment = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return (
        f"{WEEKDAYS[moment.weekday()]}, {moment.day:02d} "
        f"{MONTHS[moment.month - 1]} {moment.year} "
        f"{moment.hour:02d}:{moment.minute:02d}:{moment.second:02d} +0000"
    )


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
        debian_version=f"{version}-0.{count}.g{short_sha}",
        short_sha=short_sha,
        timestamp=timestamp,
        is_release=is_release,
    )


def _read_template(path: Path) -> str:
    """Read the changelog template and require every substitution marker."""
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


def _entry_text(source: Source) -> str:
    """Describe the build in the changelog entry."""
    if source.is_release:
        return f"Release {source.version}."
    return f"Snapshot build from commit {source.short_sha}."


def _render(template: str, source: Source) -> str:
    """Substitute the template markers and validate the result."""
    rendered = (
        template.replace("@VERSION@", source.debian_version)
        .replace("@DATE@", _format_date(source.timestamp))
        .replace("@TEXT@", _entry_text(source))
    )
    leftovers = [placeholder for placeholder in PLACEHOLDERS if placeholder in rendered]
    if leftovers:
        _fail(
            f"rendered changelog still contains placeholder(s): {', '.join(leftovers)}"
        )
    return rendered


def _extract(archive: tarfile.TarFile, destination: Path) -> None:
    """Extract a tar stream, normalising modes but keeping the executable bit."""
    # The data filter needs Python 3.10.12, which is the project's oldest
    # supported interpreter (Ubuntu 22.04).
    archive.extractall(destination, filter="data")


def _expose_archive(repo_root: Path, source_ref: str, destination: Path) -> None:
    """Stream git archive for the source ref into the destination directory."""
    process = subprocess.Popen(
        ["git", "-C", str(repo_root), "archive", "--format=tar", source_ref],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stream = process.stdout
    errors = process.stderr
    if stream is None or errors is None:  # pragma: no cover - both pipes requested
        process.kill()
        _fail("git archive did not expose its output streams")
    try:
        with tarfile.open(fileobj=stream, mode="r|") as archive:
            _extract(archive, destination)
    except (OSError, tarfile.TarError) as error:
        process.kill()
        process.wait()
        message = f"cannot extract {source_ref}: {error}"
        raise PrepareError(message) from error
    detail = errors.read().decode(errors="replace").strip()
    if process.wait() != 0:
        _fail(f"git archive failed for {source_ref}: {detail or 'unknown error'}")


def prepare(
    *,
    repo_root: Path,
    template_dir: Path,
    source_ref: str,
    build_root: Path,
) -> Source:
    """Render the source tree and packaging for a source ref."""
    if not repo_root.is_dir():
        _fail(f"repository root does not exist: {repo_root}")
    if not template_dir.is_dir():
        _fail(f"template directory does not exist: {template_dir}")
    version = _read_version(repo_root, source_ref)
    source = _source_metadata(repo_root, source_ref, version)
    template = _read_template(template_dir / "changelog")
    if not (template_dir / "rules").is_file():
        _fail(f"template directory has no rules file: {template_dir}")
    changelog = _render(template, source)

    build_root.mkdir(parents=True, exist_ok=True)
    final = build_root / f"scantpaper-{source.debian_version}"
    temporary = Path(tempfile.mkdtemp(prefix=f".{final.name}.", dir=build_root))
    try:
        _expose_archive(repo_root, source_ref, temporary)
        debian = temporary / "debian"
        shutil.copytree(template_dir, debian, ignore=shutil.ignore_patterns(README))
        (debian / "changelog").write_text(changelog, encoding="utf-8")
        (debian / "rules").chmod(0o755)
        if final.exists():
            shutil.rmtree(final)
        temporary.replace(final)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
    return source


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-ref",
        required=True,
        help="git revision whose metadata and source tree are packaged",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="git working tree root (default: current directory)",
    )
    parser.add_argument(
        "--template-dir",
        type=Path,
        default=Path("packaging/debian"),
        help="path to the packaging template in the working tree",
    )
    parser.add_argument(
        "--build-root",
        type=Path,
        default=Path("build/deb"),
        help="directory for the rendered source tree",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Render the tree, printing the Debian version, and return an exit status."""
    args = parse_args(argv)
    try:
        source = prepare(
            repo_root=args.repo_root,
            template_dir=args.template_dir,
            source_ref=args.source_ref,
            build_root=args.build_root,
        )
    except PrepareError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(source.debian_version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
