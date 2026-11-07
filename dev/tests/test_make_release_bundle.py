"""Tests for the per-distribution release bundle builder."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLE = REPO_ROOT / "dev" / "make_release_bundle.py"

APP_RPM = "scantpaper-4.0.3-0.2074.gabc123.fc43.noarch.rpm"
SANE_RPM = "python3-sane-2.9.2-1.fc43.x86_64.rpm"
DEBUGINFO_RPM = "python3-sane-debuginfo-2.9.2-1.fc43.x86_64.rpm"
DEBUGSOURCE_RPM = "python3-sane-debugsource-2.9.2-1.fc43.x86_64.rpm"


def _write_rpm(directory: Path, name: str, content: bytes = b"rpm") -> Path:
    """Write a fake RPM whose name is enough for the builder."""
    path = directory / name
    path.write_bytes(content + name.encode("utf-8"))
    return path


def _input_dir(tmp_path: Path) -> Path:
    """Create an input directory with an application and dependency RPM."""
    directory = tmp_path / "input"
    directory.mkdir()
    _write_rpm(directory, APP_RPM)
    _write_rpm(directory, SANE_RPM)
    return directory


def _run(
    *,
    input_dir: Path,
    output_dir: Path,
    target: str,
    version: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the bundle builder and return its completed process."""
    command = [
        sys.executable,
        str(BUNDLE),
        "--target",
        target,
        "--input",
        str(input_dir),
        "--output",
        str(output_dir),
    ]
    if version is not None:
        command.extend(["--version", version])
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _read_member(archive: Path, member: str) -> str:
    """Return a text member from an archive."""
    with tarfile.open(archive) as tar:
        stream = tar.extractfile(member)
        assert stream is not None
        return stream.read().decode("utf-8")


def test_unknown_target_is_rejected(tmp_path: Path) -> None:
    """Reject a target before creating an output directory."""
    input_dir = _input_dir(tmp_path)
    output_dir = tmp_path / "out"

    result = _run(input_dir=input_dir, output_dir=output_dir, target="bogus")

    assert result.returncode != 0
    assert "invalid choice" in result.stderr
    assert not output_dir.exists()


def test_version_is_read_from_the_application_rpm(tmp_path: Path) -> None:
    """Name the archive from the application RPM's version."""
    input_dir = _input_dir(tmp_path)
    output_dir = tmp_path / "out"

    result = _run(input_dir=input_dir, output_dir=output_dir, target="fedora-43")

    assert result.returncode == 0, result.stderr
    archive = output_dir / "scantpaper-4.0.3-fedora-43.tar.gz"
    assert archive.is_file()
    with tarfile.open(archive) as tar:
        names = tar.getnames()
    assert "scantpaper-4.0.3-fedora-43" in names
    assert f"scantpaper-4.0.3-fedora-43/{APP_RPM}" in names


def test_version_override_wins(tmp_path: Path) -> None:
    """Use --version when the caller supplies it."""
    input_dir = _input_dir(tmp_path)
    output_dir = tmp_path / "out"

    result = _run(
        input_dir=input_dir,
        output_dir=output_dir,
        target="fedora-43",
        version="9.9.9",
    )

    assert result.returncode == 0, result.stderr
    archive = output_dir / "scantpaper-9.9.9-fedora-43.tar.gz"
    assert archive.is_file()
    with tarfile.open(archive) as tar:
        names = tar.getnames()
    assert "scantpaper-9.9.9-fedora-43" in names
    assert f"scantpaper-9.9.9-fedora-43/{APP_RPM}" in names


def test_debug_packages_are_excluded(tmp_path: Path) -> None:
    """Leave debuginfo and debugsource RPMs out of the archive."""
    input_dir = _input_dir(tmp_path)
    _write_rpm(input_dir, DEBUGINFO_RPM)
    _write_rpm(input_dir, DEBUGSOURCE_RPM)
    output_dir = tmp_path / "out"

    result = _run(input_dir=input_dir, output_dir=output_dir, target="fedora-43")

    assert result.returncode == 0, result.stderr
    archive = output_dir / "scantpaper-4.0.3-fedora-43.tar.gz"
    with tarfile.open(archive) as tar:
        names = tar.getnames()
    assert not any("debuginfo" in name for name in names)
    assert not any("debugsource" in name for name in names)
    checksums = _read_member(archive, "scantpaper-4.0.3-fedora-43/SHA256SUMS")
    assert "debuginfo" not in checksums
    assert "debugsource" not in checksums


def test_missing_application_rpm_is_rejected(tmp_path: Path) -> None:
    """Fail when the input has dependencies but no application RPM."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    _write_rpm(input_dir, SANE_RPM)
    output_dir = tmp_path / "out"

    result = _run(input_dir=input_dir, output_dir=output_dir, target="fedora-43")

    assert result.returncode == 1
    assert "no scantpaper application RPM" in result.stderr
    assert not output_dir.exists()


def test_only_debug_rpms_are_rejected(tmp_path: Path) -> None:
    """Fail when debug filtering leaves no runtime RPM."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    _write_rpm(input_dir, DEBUGINFO_RPM)
    output_dir = tmp_path / "out"

    result = _run(input_dir=input_dir, output_dir=output_dir, target="fedora-43")

    assert result.returncode == 1
    assert "contains no runtime RPMs" in result.stderr


def test_missing_input_directory_is_rejected(tmp_path: Path) -> None:
    """Fail with a named input directory when it does not exist."""
    result = _run(
        input_dir=tmp_path / "missing",
        output_dir=tmp_path / "out",
        target="fedora-43",
    )

    assert result.returncode == 1
    assert "input directory does not exist" in result.stderr


def test_archive_layout_and_checksums(tmp_path: Path) -> None:
    """Lay out the archive and checksum every RPM."""
    input_dir = _input_dir(tmp_path)
    output_dir = tmp_path / "out"
    result = _run(input_dir=input_dir, output_dir=output_dir, target="fedora-43")
    assert result.returncode == 0, result.stderr
    archive = output_dir / "scantpaper-4.0.3-fedora-43.tar.gz"
    stem = "scantpaper-4.0.3-fedora-43"

    with tarfile.open(archive) as tar:
        names = set(tar.getnames())
        checksum_stream = tar.extractfile(f"{stem}/SHA256SUMS")
        assert checksum_stream is not None
        checksums = checksum_stream.read().decode("utf-8")

    assert names == {
        stem,
        f"{stem}/INSTALL.txt",
        f"{stem}/SHA256SUMS",
        f"{stem}/{APP_RPM}",
        f"{stem}/{SANE_RPM}",
    }
    expected: dict[str, str] = {}
    for line in checksums.splitlines():
        digest, name = line.split("  ", 1)
        expected[name] = digest
    assert set(expected) == {APP_RPM, SANE_RPM}
    for name, digest in expected.items():
        assert hashlib.sha256((input_dir / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize(
    ("target", "command"),
    [
        ("fedora-43", "sudo dnf install ./*.rpm"),
        ("fedora-44", "sudo dnf install ./*.rpm"),
        (
            "opensuse-leap-16.0",
            "sudo zypper install --allow-unsigned-rpm ./*.rpm",
        ),
        (
            "opensuse-tumbleweed",
            "sudo zypper install --allow-unsigned-rpm ./*.rpm",
        ),
    ],
)
def test_install_note_names_the_target_command(
    tmp_path: Path, target: str, command: str
) -> None:
    """Write the target's one-transaction install command."""
    input_dir = _input_dir(tmp_path)
    output_dir = tmp_path / "out"

    result = _run(input_dir=input_dir, output_dir=output_dir, target=target)

    assert result.returncode == 0, result.stderr
    stem = f"scantpaper-4.0.3-{target}"
    note = _read_member(output_dir / f"{stem}.tar.gz", f"{stem}/INSTALL.txt")
    assert f"cd {stem}" in note
    assert command in note
    if target.startswith("opensuse-"):
        assert "--allow-unsigned-rpm is required" in note


def test_member_order_and_metadata_are_normalized(tmp_path: Path) -> None:
    """Produce the same sorted, normalized member list on every build."""
    input_dir = _input_dir(tmp_path)
    first = tmp_path / "first"
    second = tmp_path / "second"
    for output_dir in (first, second):
        result = _run(
            input_dir=input_dir,
            output_dir=output_dir,
            target="fedora-43",
        )
        assert result.returncode == 0, result.stderr

    archive = "scantpaper-4.0.3-fedora-43.tar.gz"
    with tarfile.open(first / archive) as left, tarfile.open(second / archive) as right:
        left_members = left.getmembers()
        right_members = right.getmembers()
        left_names = [member.name for member in left_members]
        right_names = [member.name for member in right_members]
        assert left_names == right_names
        assert left_names == sorted(left_names)
        for member in left_members:
            assert member.uid == 0
            assert member.gid == 0
            assert member.uname == ""
            assert member.gname == ""
            assert member.mtime == 0
            assert member.mode == (0o755 if member.isdir() else 0o644)
