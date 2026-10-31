"""Build per-series Ubuntu PPA source packages from the synced Debian tree.

Run from a clean salsa checkout after the Debian sync has been committed:

    python3 dev/build_ppa.py --all
    python3 dev/build_ppa.py --series noble --dry-run

Each series is built from a throwaway tree of the Debian branch, with the
series' ``debhelper-compat`` and any configured test-dependency removals from
``packaging/ubuntu/suites.toml``, the version ``<upstream>-0~ppa1<series>`` and
``Distribution: <series>``. The pristine-tar orig tarball is reused.

Sources are built unsigned. ``debsign`` and ``dput`` are printed, never run.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final, NoReturn

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

MATRIX: Final = "packaging/ubuntu/suites.toml"
CHANGELOG: Final = "debian/changelog"
CONTROL: Final = "debian/control"
TESTS_CONTROL: Final = "debian/tests/control"
COMPAT_RE: Final = re.compile(r"debhelper-compat \(= \d+\)")
VERSION_RE: Final = re.compile(r"(?m)^scantpaper \(([^)]+)\)")
DISTRIBUTION_RE: Final = re.compile(r"(?m)^scantpaper \([^)]+\) \S+;")


class PpaError(Exception):
    """Raised when a series source package cannot be prepared."""


def _fail(message: str) -> NoReturn:
    """Raise a build error with a message built by the caller."""
    raise PpaError(message)


@dataclass(frozen=True)
class SeriesSpec:
    """The differences a series needs."""

    name: str
    version: str
    compat: int
    test_depends_to_drop: tuple[str, ...]


@dataclass(frozen=True)
class TreeSource:
    """Where a series tree comes from and where its package is written."""

    root: Path
    branch: str
    upstream: str
    series_dir: Path
    orig: Path


@dataclass(frozen=True)
class Context:
    """State shared by every selected series."""

    root: Path
    branch: str
    upstream: str
    output: Path
    orig: Path
    dput_target: str
    dry_run: bool


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a command in ``root`` without raising."""
    return subprocess.run(
        [*args],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )


def _git(root: Path, *args: str) -> str:
    """Run git in ``root`` and return stripped output."""
    result = _run(root, "git", *args)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        _fail(f"git {' '.join(args)} failed: {detail or 'unknown error'}")
    return result.stdout.strip()


def _matrix(path: Path) -> dict[str, dict[str, object]]:
    """Read and validate the suite matrix."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        message = f"cannot read {path}: {error}"
        raise PpaError(message) from error
    series = data.get("series")
    if not isinstance(series, dict):
        _fail(f"{path} has no [series.<name>] tables")
    validated: dict[str, dict[str, object]] = {}
    for name, settings in series.items():
        if not isinstance(settings, dict):
            _fail(f"series {name} is not a table")
        compat = settings.get("debhelper-compat")
        if not isinstance(compat, int) or isinstance(compat, bool):
            _fail(f"series {name} has no integer debhelper-compat")
        drops = settings.get("drop-test-depends", [])
        if not isinstance(drops, list) or not all(
            isinstance(item, str) for item in drops
        ):
            _fail(f"series {name} has an invalid drop-test-depends")
        validated[str(name)] = {"debhelper-compat": compat, "drops": drops}
    return validated


def _upstream_version(root: Path) -> str:
    """Return the upstream part of the synced Debian version."""
    try:
        text = (root / CHANGELOG).read_text(encoding="utf-8")
    except OSError as error:
        message = f"cannot read {root / CHANGELOG}: {error}"
        raise PpaError(message) from error
    match = VERSION_RE.search(text)
    if match is None:
        _fail("debian/changelog has no scantpaper entry")
    version = str(match.group(1))
    if "-" not in version:
        _fail(f"version {version} has no Debian revision; run the sync first")
    return version.rsplit("-", 1)[0]


def _orig_tarball(root: Path, upstream: str) -> Path:
    """Find or export the orig tarball for ``upstream``."""
    candidates = sorted(root.parent.glob(f"scantpaper_{upstream}.orig.tar.*"))
    if candidates:
        return candidates[0]
    if shutil.which("gbp") is None:
        _fail(
            f"no orig tarball for {upstream}; install gbp or place one next to "
            "the checkout"
        )
    result = _run(root, "gbp", "export-orig", "--pristine-tar")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        _fail(
            f"cannot create the orig tarball for {upstream}: "
            f"{detail or 'unknown error'}"
        )
    candidates = sorted(root.parent.glob(f"scantpaper_{upstream}.orig.tar.*"))
    if not candidates:
        _fail(f"gbp export-orig did not create an orig tarball for {upstream}")
    return candidates[0]


def _extract_tree(root: Path, branch: str, destination: Path) -> None:
    """Extract the committed branch into a throwaway tree."""
    destination.mkdir(parents=True)
    process = subprocess.Popen(
        ["git", "-C", str(root), "archive", "--format=tar", branch],
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
            archive.extractall(destination, filter="data")
    except (OSError, tarfile.TarError) as error:
        process.kill()
        process.wait()
        message = f"cannot extract {branch}: {error}"
        raise PpaError(message) from error
    detail = errors.read().decode(errors="replace").strip()
    if process.wait() != 0:
        _fail(f"git archive failed for {branch}: {detail or 'unknown error'}")


def _rewrite_changelog(path: Path, version: str, series: str) -> None:
    """Replace the top entry's version and distribution."""
    text = path.read_text(encoding="utf-8")
    replaced, count = DISTRIBUTION_RE.subn(
        f"scantpaper ({version}) {series};", text, count=1
    )
    if count != 1:
        _fail(f"cannot rewrite the top entry of {path}")
    path.write_text(replaced, encoding="utf-8")


def _rewrite_control(path: Path, compat: int) -> None:
    """Set the series' debhelper compatibility level."""
    text = path.read_text(encoding="utf-8")
    replaced, count = COMPAT_RE.subn(f"debhelper-compat (= {compat})", text)
    if count != 1:
        _fail(f"expected one debhelper-compat in {path}, found {count}")
    path.write_text(replaced, encoding="utf-8")


def _drop_test_depends(path: Path, depends: tuple[str, ...]) -> None:
    """Remove test dependencies the series does not carry."""
    text = path.read_text(encoding="utf-8")
    for name in depends:
        pattern = re.compile(rf"(?m)^ {re.escape(name)},?$\n?")
        text, count = pattern.subn("", text)
        if count == 0:
            _fail(f"{name} is not in {path}")
    path.write_text(text, encoding="utf-8")


def _provides(text: str) -> set[int]:
    """Return the compat levels a debhelper package advertises."""
    return {int(value) for value in re.findall(r"debhelper-compat \(= (\d+)\)", text)}


def _verify_series(series: str, compat: int) -> None:
    """Check the configured compat against the series' archive."""
    runtime = shutil.which("podman") or shutil.which("docker")
    if runtime is None:
        _fail("--verify needs podman or docker")
    script = "apt-get update -qq >/dev/null 2>&1 && apt-cache show debhelper"
    result = subprocess.run(
        [runtime, "run", "--rm", f"ubuntu:{series}", "bash", "-c", script],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        _fail(f"cannot query ubuntu:{series}: {detail or 'unknown error'}")
    available = _provides(result.stdout)
    if compat not in available:
        _fail(f"{series} does not provide debhelper-compat {compat}")
    print(f"{series}: debhelper-compat {compat} verified")


def _spec(series: str, settings: dict[str, object], upstream: str) -> SeriesSpec:
    """Build a validated series specification."""
    compat = settings.get("debhelper-compat")
    if not isinstance(compat, int) or isinstance(compat, bool):
        _fail(f"series {series} has no integer debhelper-compat")
    drops = settings.get("drops", [])
    if not isinstance(drops, list):
        drops = []
    return SeriesSpec(
        name=series,
        version=f"{upstream}-0~ppa1{series}",
        compat=compat,
        test_depends_to_drop=tuple(str(item) for item in drops),
    )


def _prepare_tree(source: TreeSource, spec: SeriesSpec) -> Path:
    """Create the series tree with its differences applied."""
    tree = source.series_dir / f"scantpaper-{source.upstream}"
    if tree.exists():
        shutil.rmtree(tree)
    _extract_tree(source.root, source.branch, tree)
    _rewrite_changelog(tree / CHANGELOG, spec.version, spec.name)
    _rewrite_control(tree / CONTROL, spec.compat)
    if spec.test_depends_to_drop:
        _drop_test_depends(tree / TESTS_CONTROL, spec.test_depends_to_drop)
    shutil.copy2(source.orig, source.series_dir / source.orig.name)
    return tree


def _build(tree: Path) -> None:
    """Build an unsigned source package."""
    result = _run(tree, "debuild", "-S", "-us", "-uc", "-sa")
    if result.returncode != 0:
        tail = "\n".join((result.stdout + result.stderr).splitlines()[-15:])
        _fail(f"debuild failed in {tree}:\n{tail}")


def _changes_file(series_dir: Path) -> Path:
    """Return the single .changes produced for a series."""
    changes = sorted(series_dir.glob("*.changes"))
    if len(changes) != 1:
        _fail(f"expected one .changes in {series_dir}, found {len(changes)}")
    return changes[0]


def _print_commands(changes: Path, target: str) -> None:
    """Print the signing and upload commands."""
    print("Next steps:")
    print(f"  debsign {changes}")
    print(f"  dput {target} {changes}")


def _output_dir(root: Path, configured: Path) -> Path:
    """Resolve the output directory against the checkout."""
    return configured if configured.is_absolute() else root / configured


def _load(
    args: argparse.Namespace,
) -> tuple[Path, dict[str, dict[str, object]], list[str]]:
    """Validate the checkout and return the root, matrix and selection."""
    root = Path(str(args.root)).resolve()
    matrix_name = str(args.matrix)
    matrix_path = root / matrix_name
    if not (root / CHANGELOG).is_file():
        _fail(f"no {CHANGELOG}; this is not a salsa checkout")
    if not matrix_path.is_file():
        _fail(f"no {matrix_name}; add the suite matrix first")
    if _git(root, "diff", "--name-only", "HEAD", "--", "debian", "packaging"):
        _fail("uncommitted packaging changes; commit or clean the Debian sync first")
    _git(root, "rev-parse", "--verify", str(args.debian_branch))
    matrix = _matrix(matrix_path)
    selected = (
        sorted(matrix) if args.all else [str(name) for name in (args.series or [])]
    )
    if not selected:
        _fail("select --all or at least one --series")
    unknown = [name for name in selected if name not in matrix]
    if unknown:
        _fail("unknown series: " + ", ".join(unknown))
    return root, matrix, selected


def _build_series(context: Context, spec: SeriesSpec) -> None:
    """Prepare, build and report one series."""
    series_dir = context.output / spec.name
    series_dir.mkdir(parents=True, exist_ok=True)
    tree = _prepare_tree(
        TreeSource(
            root=context.root,
            branch=context.branch,
            upstream=context.upstream,
            series_dir=series_dir,
            orig=context.orig,
        ),
        spec,
    )
    if context.dry_run:
        print(f"{spec.name}: prepared {tree} for {spec.version}")
        _print_commands(
            series_dir / f"scantpaper_{spec.version}_source.changes",
            context.dput_target,
        )
        return
    _build(tree)
    changes = _changes_file(series_dir)
    shutil.rmtree(tree)
    print(f"{spec.name}: built {changes}")
    _print_commands(changes, context.dput_target)


def build(args: argparse.Namespace) -> None:
    """Prepare and optionally build the selected series."""
    root, matrix, selected = _load(args)
    if args.verify:
        for series in selected:
            spec = _spec(series, matrix[series], "0")
            _verify_series(series, spec.compat)
    upstream = _upstream_version(root)
    context = Context(
        root=root,
        branch=args.debian_branch,
        upstream=upstream,
        output=_output_dir(root, args.output_dir),
        orig=_orig_tarball(root, upstream),
        dput_target=args.dput_target,
        dry_run=args.dry_run,
    )
    context.output.mkdir(parents=True, exist_ok=True)
    for series in selected:
        _build_series(context, _spec(series, matrix[series], upstream))


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
        "--matrix",
        default=MATRIX,
        help=f"suite matrix relative to the root (default: {MATRIX})",
    )
    parser.add_argument(
        "--debian-branch",
        default="debian/master",
        help="branch to package (default: debian/master)",
    )
    parser.add_argument("--series", action="append", help="series to build")
    parser.add_argument("--all", action="store_true", help="build every series")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/ppa"),
        help="directory for the source packages (default: build/ppa)",
    )
    parser.add_argument(
        "--dput-target",
        default="gscan2pdf-ppa",
        help="dput target to print (default: gscan2pdf-ppa)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="check each compat against its series archive in a container",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="prepare the trees and print the commands without building",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Build the selected series, returning a process exit status."""
    args = parse_args(argv)
    try:
        build(args)
    except PpaError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
