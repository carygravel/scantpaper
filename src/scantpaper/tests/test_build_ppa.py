"""Tests for dev/build_ppa.py."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="git is not available",
)

REPO_ROOT = Path(__file__).resolve().parents[3]
BUILD = REPO_ROOT / "dev" / "build_ppa.py"

CHANGELOG = """scantpaper (4.0.2-1) unstable; urgency=medium

  * New upstream release.

 -- Test Packager <test@example.com>  Sun, 25 Oct 2026 00:00:00 +0000
"""

CONTROL = """Source: scantpaper
Section: utils
Maintainer: Debian Python Team <team+python@tracker.debian.org>
Build-Depends: debhelper-compat (= 14),
               dh-python

Package: scantpaper
Architecture: all
"""

TESTS_CONTROL = """Tests: test-suite
Depends: @,
 jbig2,
 python3-polib,
"""

MATRIX = """[series.noble]
debhelper-compat = 13

[series.jammy]
debhelper-compat = 13
drop-test-depends = ["jbig2"]
"""


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    """Run git in ``repo`` and return stripped output."""
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()


def _commit(repo: Path) -> None:
    """Stage everything and commit it."""
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": "2026-10-31T12:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-10-31T12:00:00+00:00",
    }
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "synced packaging", env=env)


def _init_repo(tmp_path: Path) -> Path:
    """Create a clean salsa-like checkout with a matrix and an orig tarball."""
    repo = tmp_path / "salsa"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "debian/master")
    _git(repo, "config", "user.name", "Test Packager")
    _git(repo, "config", "user.email", "test@example.com")
    debian = repo / "debian"
    debian.mkdir()
    (debian / "changelog").write_text(CHANGELOG, encoding="utf-8")
    (debian / "control").write_text(CONTROL, encoding="utf-8")
    (debian / "tests").mkdir()
    (debian / "tests" / "control").write_text(TESTS_CONTROL, encoding="utf-8")
    ubuntu = repo / "packaging" / "ubuntu"
    ubuntu.mkdir(parents=True)
    (ubuntu / "suites.toml").write_text(MATRIX, encoding="utf-8")
    _commit(repo)
    (tmp_path / "scantpaper_4.0.2.orig.tar.gz").write_bytes(b"orig\n")
    return repo


def _run(
    repo: Path,
    output: Path,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    """Run the PPA tool and return the completed process."""
    return subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--root",
            str(repo),
            "--output-dir",
            str(output),
            *extra,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_noble_dry_run_rewrites_the_tree(tmp_path: Path) -> None:
    """Apply the noble compat, version and distribution."""
    repo = _init_repo(tmp_path)
    output = tmp_path / "out"

    result = _run(repo, output, "--series", "noble", "--dry-run")

    assert result.returncode == 0, result.stdout + result.stderr
    tree = output / "noble" / "scantpaper-4.0.2"
    assert tree.is_dir()
    changelog = (tree / "debian" / "changelog").read_text()
    assert changelog.startswith(
        "scantpaper (4.0.2-0~ppa1noble) noble; urgency=medium\n"
    )
    control = (tree / "debian" / "control").read_text()
    assert "debhelper-compat (= 13)" in control
    assert "debhelper-compat (= 14)" not in control
    assert " jbig2," in (tree / "debian" / "tests" / "control").read_text()
    assert "debsign" in result.stdout
    assert "dput gscan2pdf-ppa" in result.stdout
    assert _git(repo, "status", "--porcelain") == ""


def test_jammy_drops_the_test_dependency(tmp_path: Path) -> None:
    """Remove a test dependency the series does not carry."""
    repo = _init_repo(tmp_path)
    output = tmp_path / "out"

    result = _run(repo, output, "--series", "jammy", "--dry-run")

    assert result.returncode == 0, result.stdout + result.stderr
    tests = output / "jammy" / "scantpaper-4.0.2" / "debian" / "tests" / "control"
    text = tests.read_text()
    assert "jbig2" not in text
    assert "python3-polib" in text


def test_dirty_packaging_is_refused(tmp_path: Path) -> None:
    """Refuse to build from uncommitted packaging changes."""
    repo = _init_repo(tmp_path)
    changelog = repo / "debian" / "changelog"
    changelog.write_text(changelog.read_text() + "\n", encoding="utf-8")

    result = _run(repo, tmp_path / "out", "--series", "noble", "--dry-run")

    assert result.returncode != 0
    assert "uncommitted packaging changes" in result.stdout + result.stderr


def test_build_artifacts_are_tolerated(tmp_path: Path) -> None:
    """Ignore untracked build output such as debian/files."""
    repo = _init_repo(tmp_path)
    (repo / "debian" / "files").write_text("scantpaper_4.0.2-1_source.changes\n")

    result = _run(repo, tmp_path / "out", "--series", "noble", "--dry-run")

    assert result.returncode == 0, result.stdout + result.stderr


def test_unknown_series_is_refused(tmp_path: Path) -> None:
    """Name a series the matrix does not know."""
    repo = _init_repo(tmp_path)

    result = _run(repo, tmp_path / "out", "--series", "oracular", "--dry-run")

    assert result.returncode != 0
    assert "unknown series: oracular" in result.stdout + result.stderr


def test_missing_orig_tarball_fails(tmp_path: Path) -> None:
    """Report a missing orig when gbp cannot export one."""
    repo = _init_repo(tmp_path)
    (tmp_path / "scantpaper_4.0.2.orig.tar.gz").unlink()

    result = _run(repo, tmp_path / "out", "--series", "noble", "--dry-run")

    assert result.returncode != 0
    assert "export-orig" in result.stdout + result.stderr
