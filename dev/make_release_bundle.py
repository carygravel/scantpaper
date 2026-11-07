"""Create a per-distribution release bundle from a directory of RPMs.

The bundle keeps the canonical RPM filenames, adds a checksum file and an
install note, and wraps the set in one archive so a user downloads one file
per distribution instead of a flat list of RPMs.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Final, NoReturn

INSTALL_COMMANDS: Final = {
    "fedora-43": "sudo dnf install ./*.rpm",
    "fedora-44": "sudo dnf install ./*.rpm",
    "opensuse-leap-16.0": "sudo zypper install --allow-unsigned-rpm ./*.rpm",
    "opensuse-tumbleweed": "sudo zypper install --allow-unsigned-rpm ./*.rpm",
}
DEBUG_MARKERS: Final = ("-debuginfo-", "-debugsource-")
CHUNK_SIZE: Final = 1024 * 1024
RPM_FILENAME_PARTS: Final = 3


class BundleError(Exception):
    """Raised when a release bundle cannot be built."""


def _fail(message: str) -> NoReturn:
    """Raise a bundle error with a message built by the caller."""
    raise BundleError(message)


def _rpm_files(directory: Path) -> list[Path]:
    """Return the RPM files in a directory, sorted by name."""
    try:
        entries = list(directory.iterdir())
    except OSError as error:
        _fail(f"cannot read input directory {directory}: {error}")
    return sorted(
        (entry for entry in entries if entry.is_file() and entry.suffix == ".rpm"),
        key=lambda path: path.name,
    )


def _is_debug(path: Path) -> bool:
    """Return whether an RPM is a debug or debug-source package."""
    return any(marker in path.name for marker in DEBUG_MARKERS)


def _runtime_rpms(directory: Path) -> list[Path]:
    """Return the runtime RPMs, excluding debug packages."""
    rpms = [path for path in _rpm_files(directory) if not _is_debug(path)]
    if not rpms:
        _fail(f"input directory {directory} contains no runtime RPMs")
    return rpms


def _application_rpm(rpms: list[Path]) -> Path:
    """Return the single ScantPaper application RPM."""
    applications = [path for path in rpms if path.name.startswith("scantpaper-")]
    if not applications:
        _fail("input contains no scantpaper application RPM")
    if len(applications) > 1:
        names = ", ".join(path.name for path in applications)
        _fail(f"input contains more than one scantpaper application RPM: {names}")
    return applications[0]


def _version_from_rpm(path: Path) -> str:
    """Read the upstream version from an RPM filename."""
    parts = path.name.split("-", 2)
    if len(parts) != RPM_FILENAME_PARTS or parts[0] != "scantpaper" or not parts[1]:
        _fail(f"cannot derive the version from RPM filename {path.name}")
    return parts[1]


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
                digest.update(chunk)
    except OSError as error:
        _fail(f"cannot read {path}: {error}")
    return digest.hexdigest()


def _install_note(target: str, version: str, stem: str) -> str:
    """Build the install note placed inside the bundle."""
    lines = [
        f"ScantPaper {version} for {target}",
        "",
        "Install the whole set in one transaction:",
        "",
        f"    cd {stem}",
        f"    {INSTALL_COMMANDS[target]}",
        "",
        "Verify the RPMs first:",
        "",
        "    sha256sum -c SHA256SUMS",
    ]
    if target.startswith("opensuse-"):
        lines.extend(
            [
                "",
                "The RPMs are unsigned, so --allow-unsigned-rpm is required.",
            ]
        )
    return "\n".join(lines) + "\n"


def _stage(*, target: str, version: str, rpms: list[Path], staging_root: Path) -> str:
    """Copy the runtime RPMs and metadata into the bundle directory."""
    stem = f"scantpaper-{version}-{target}"
    bundle_dir = staging_root / stem
    try:
        bundle_dir.mkdir(parents=True)
        for rpm in rpms:
            shutil.copy2(rpm, bundle_dir / rpm.name)
        checksums = "\n".join(f"{_sha256(rpm)}  {rpm.name}" for rpm in rpms) + "\n"
        (bundle_dir / "SHA256SUMS").write_text(checksums, encoding="utf-8")
        note = _install_note(target, version, stem)
        (bundle_dir / "INSTALL.txt").write_text(note, encoding="utf-8")
    except OSError as error:
        _fail(f"cannot stage the release bundle: {error}")
    return stem


def _tar_info(archive: tarfile.TarFile, path: Path, arcname: str) -> tarfile.TarInfo:
    """Create normalized tar metadata for a staged path."""
    try:
        info = archive.gettarinfo(str(path), arcname=arcname)
    except OSError as error:
        _fail(f"cannot read {path}: {error}")
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    info.mode = 0o755 if info.isdir() else 0o644
    return info


def _write_archive(staging_root: Path, destination: Path) -> None:
    """Write a tar archive of the staging tree with normalized metadata."""
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
    except OSError as error:
        _fail(f"cannot prepare archive {destination}: {error}")
    try:
        with (
            temporary.open("wb") as raw,
            gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed,
            tarfile.open(
                fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT
            ) as archive,
        ):
            for path in sorted(staging_root.rglob("*")):
                arcname = str(path.relative_to(staging_root))
                info = _tar_info(archive, path, arcname)
                if info.isfile():
                    with path.open("rb") as source:
                        archive.addfile(info, source)
                else:
                    archive.addfile(info)
        temporary.chmod(0o644)
        temporary.replace(destination)
    except (OSError, tarfile.TarError) as error:
        _fail(f"cannot write archive {destination}: {error}")
    finally:
        temporary.unlink(missing_ok=True)


def build(
    *,
    target: str,
    input_dir: Path,
    output_dir: Path,
    version: str | None = None,
) -> Path:
    """Build one target's release archive and return its path."""
    if target not in INSTALL_COMMANDS:
        supported = ", ".join(sorted(INSTALL_COMMANDS))
        _fail(f"unknown target {target}; expected one of: {supported}")
    if not input_dir.is_dir():
        _fail(f"input directory does not exist: {input_dir}")
    rpms = _runtime_rpms(input_dir)
    application = _application_rpm(rpms)
    resolved_version = version or _version_from_rpm(application)
    if not resolved_version:
        _fail("version must not be empty")
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        _fail(f"cannot create output directory {output_dir}: {error}")
    stem = f"scantpaper-{resolved_version}-{target}"
    destination = output_dir / f"{stem}.tar.gz"
    try:
        with tempfile.TemporaryDirectory(
            dir=output_dir, prefix=".bundle."
        ) as temporary:
            staging_root = Path(temporary)
            staged = _stage(
                target=target,
                version=resolved_version,
                rpms=rpms,
                staging_root=staging_root,
            )
            if staged != stem:
                _fail("internal staging name mismatch")
            _write_archive(staging_root, destination)
    except OSError as error:
        _fail(f"cannot build the release bundle: {error}")
    return destination


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        required=True,
        choices=sorted(INSTALL_COMMANDS),
        help="distribution target for the archive",
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="directory containing the target's runtime RPMs",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="directory for the generated .tar.gz",
    )
    parser.add_argument(
        "--version",
        help="override the version derived from the application RPM",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Build a release bundle, returning a process exit status."""
    args = parse_args(argv)
    try:
        build(
            target=args.target,
            input_dir=args.input,
            output_dir=args.output,
            version=args.version,
        )
    except BundleError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
