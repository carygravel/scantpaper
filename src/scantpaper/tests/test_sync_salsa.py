"""Tests for dev/sync_salsa.py."""

from __future__ import annotations

import datetime
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
SYNC = REPO_ROOT / "dev" / "sync_salsa.py"

PYPROJECT = """[project]
name = "scantpaper"
version = "{version}"
"""

OLD_CONTROL = """Source: scantpaper
Section: utils
Maintainer: Debian Python Team <team+python@tracker.debian.org>
Build-Depends: debhelper-compat (= 14),
               python3-wheel

Package: scantpaper
Architecture: all
"""

NEW_CONTROL = """Source: scantpaper
Section: utils
Maintainer: Debian Python Team <team+python@tracker.debian.org>
Build-Depends: debhelper-compat (= 14),
               python3-cysignals-bare

Package: scantpaper
Architecture: all
"""

OLD_RULES = """#!/usr/bin/make -f

%:
\tdh $@
"""

NEW_RULES = """#!/usr/bin/make -f

%:
\tdh $@ --with python3
"""

OLD_CHANGELOG = """scantpaper (4.0.1-1) unstable; urgency=medium

  * New upstream release.

 -- Test Packager <test@example.com>  Sun, 25 Oct 2026 00:00:00 +0000

scantpaper (4.0.0-1) unstable; urgency=medium

  * New upstream release.

 -- Test Packager <test@example.com>  Sat, 24 Oct 2026 00:00:00 +0000
"""

CHANGELOG_TEMPLATE = """scantpaper (@VERSION@) unstable; urgency=medium

  * @TEXT@

 -- Test Packager <test@example.com>  @DATE@
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


def _commit(repo: Path, message: str) -> None:
    """Stage everything and commit it."""
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": "2026-10-25T12:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-10-25T12:00:00+00:00",
    }
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", message, env=env)


def _init_repo(tmp_path: Path, *, same_upstream: bool = False) -> Path:
    """Create a salsa-like checkout with a released tag and a new import."""
    repo = tmp_path / "salsa"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "debian/master")
    _git(repo, "config", "user.name", "Test Packager")
    _git(repo, "config", "user.email", "test@example.com")

    (repo / "pyproject.toml").write_text(
        PYPROJECT.format(version="4.0.1"), encoding="utf-8"
    )
    packaging = repo / "packaging" / "debian"
    packaging.mkdir(parents=True)
    (packaging / "control").write_text(OLD_CONTROL, encoding="utf-8")
    (packaging / "rules").write_text(OLD_RULES, encoding="utf-8")
    (packaging / "scantpaper.install").write_text(
        "screenshot.png usr/share/doc/scantpaper/\n", encoding="utf-8"
    )
    (packaging / "changelog").write_text(CHANGELOG_TEMPLATE, encoding="utf-8")
    (packaging / "README.md").write_text("docs\n", encoding="utf-8")

    debian = repo / "debian"
    debian.mkdir()
    (debian / "control").write_text(OLD_CONTROL, encoding="utf-8")
    (debian / "rules").write_text(OLD_RULES, encoding="utf-8")
    (debian / "scantpaper.install").write_text(
        "screenshot.png usr/share/doc/scantpaper/\n", encoding="utf-8"
    )
    (debian / "changelog").write_text(OLD_CHANGELOG, encoding="utf-8")

    _commit(repo, "released 4.0.1-1")
    _git(repo, "tag", "debian/4.0.1-1")

    version = "4.0.1" if same_upstream else "4.0.2"
    (repo / "pyproject.toml").write_text(
        PYPROJECT.format(version=version), encoding="utf-8"
    )
    (packaging / "scantpaper.install").unlink()
    (packaging / "control").write_text(NEW_CONTROL, encoding="utf-8")
    (packaging / "rules").write_text(NEW_RULES, encoding="utf-8")
    (packaging / "tests").mkdir()
    (packaging / "tests" / "control").write_text(
        "Tests: test-suite\nDepends: @, git,\n", encoding="utf-8"
    )
    _git(repo, "tag", f"upstream/{version}")
    return repo


def _run(
    repo: Path,
    *extra: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the sync tool and return the completed process."""
    return subprocess.run(
        [sys.executable, str(SYNC), "--root", str(repo), *extra],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def _snapshot(repo: Path) -> dict[str, str]:
    """Return the content of every file under debian/."""
    return {
        path.relative_to(repo).as_posix(): path.read_text(encoding="utf-8")
        for path in (repo / "debian").rglob("*")
        if path.is_file()
    }


def test_sync_copies_and_drafts(tmp_path: Path) -> None:
    """Copy the shared tree, delete stale files and draft the entry."""
    repo = _init_repo(tmp_path)

    result = _run(repo, "--date", "2026-11-01")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / "debian" / "control").read_text() == NEW_CONTROL
    assert not (repo / "debian" / "scantpaper.install").exists()
    assert (repo / "debian" / "tests" / "control").is_file()
    changelog = (repo / "debian" / "changelog").read_text()
    assert changelog.startswith("scantpaper (4.0.2-1) unstable; urgency=medium\n")
    assert "Sun, 01 Nov 2026 00:00:00 +0000" in changelog
    assert "  * New upstream release." in changelog
    assert "    debian/tests/control: new" in changelog
    assert "    debian/scantpaper.install: removed" in changelog
    assert "    Build-Depends: +python3-cysignals-bare, -python3-wheel" in changelog
    assert "scantpaper (4.0.1-1)" in changelog
    assert _git(repo, "rev-list", "--count", "HEAD") == "1"
    assert "debuild -S -sa" in result.stdout
    assert "dput ftp-master" in result.stdout


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    """Report the plan without touching the tree."""
    repo = _init_repo(tmp_path)
    before = _snapshot(repo)

    result = _run(repo, "--date", "2026-11-01", "--dry-run")

    assert result.returncode == 0, result.stdout + result.stderr
    assert _snapshot(repo) == before
    assert "Would draft debian/changelog entry 4.0.2-1" in result.stdout
    assert "scantpaper (4.0.2-1)" in result.stdout


def test_leftover_file_fails(tmp_path: Path) -> None:
    """Fail, naming a file salsa must not own."""
    repo = _init_repo(tmp_path)
    patches = repo / "debian" / "patches"
    patches.mkdir()
    (patches / "series").write_text("privacy\n", encoding="utf-8")
    before = (repo / "debian" / "control").read_text()

    result = _run(repo, "--date", "2026-11-01")

    assert result.returncode != 0
    assert "debian/patches/series" in result.stdout + result.stderr
    assert (repo / "debian" / "control").read_text() == before


def test_same_upstream_increments_revision(tmp_path: Path) -> None:
    """Draft a packaging-only upload with the next revision."""
    repo = _init_repo(tmp_path, same_upstream=True)

    result = _run(repo, "--date", "2026-11-01")

    assert result.returncode == 0, result.stdout + result.stderr
    changelog = (repo / "debian" / "changelog").read_text()
    assert changelog.startswith("scantpaper (4.0.1-2) unstable; urgency=medium\n")
    assert "  * Debian packaging update." in changelog


def test_wrong_branch_fails(tmp_path: Path) -> None:
    """Refuse to write from a branch that is not the Debian branch."""
    repo = _init_repo(tmp_path)
    _git(repo, "checkout", "-q", "-b", "other")

    result = _run(repo, "--date", "2026-11-01")

    assert result.returncode != 0
    assert "expected 'debian/master'" in result.stdout + result.stderr


def test_missing_import_tag_fails(tmp_path: Path) -> None:
    """Refuse to run before the new upstream version has been imported."""
    repo = _init_repo(tmp_path)
    _git(repo, "tag", "-d", "upstream/4.0.2")

    result = _run(repo, "--date", "2026-11-01")

    assert result.returncode != 0
    assert "gbp import-orig" in result.stdout + result.stderr


def test_rerun_replaces_the_draft(tmp_path: Path) -> None:
    """Keep one entry when the sync is run twice."""
    repo = _init_repo(tmp_path)

    first = _run(repo, "--date", "2026-11-01")
    second = _run(repo, "--date", "2026-11-01")

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    changelog = (repo / "debian" / "changelog").read_text()
    assert changelog.count("scantpaper (4.0.2-1)") == 1
    assert changelog.count("scantpaper (4.0.1-1)") == 1


def test_pre_migration_release_needs_a_clean_slate(tmp_path: Path) -> None:
    """Copy the first packaging tree when the previous release had none."""
    repo = tmp_path / "salsa"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "debian/master")
    _git(repo, "config", "user.name", "Test Packager")
    _git(repo, "config", "user.email", "test@example.com")
    (repo / "pyproject.toml").write_text(
        PYPROJECT.format(version="4.0.1"), encoding="utf-8"
    )
    (repo / "debian").mkdir()
    (repo / "debian" / "changelog").write_text(OLD_CHANGELOG, encoding="utf-8")
    _commit(repo, "released 4.0.1-1")
    _git(repo, "tag", "debian/4.0.1-1")
    packaging = repo / "packaging" / "debian"
    packaging.mkdir(parents=True)
    (packaging / "control").write_text(NEW_CONTROL, encoding="utf-8")
    (packaging / "rules").write_text(NEW_RULES, encoding="utf-8")
    (packaging / "changelog").write_text(CHANGELOG_TEMPLATE, encoding="utf-8")
    _git(repo, "tag", "upstream/4.0.1")

    result = _run(repo, "--date", "2026-11-01")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / "debian" / "control").read_text() == NEW_CONTROL
    changelog = (repo / "debian" / "changelog").read_text()
    assert changelog.startswith("scantpaper (4.0.1-2) unstable; urgency=medium\n")
    assert "debian/control: new" not in changelog


def test_pre_migration_release_with_leftovers_fails(tmp_path: Path) -> None:
    """Name the leftovers when the baseline has no packaging tree."""
    repo = tmp_path / "salsa"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "debian/master")
    _git(repo, "config", "user.name", "Test Packager")
    _git(repo, "config", "user.email", "test@example.com")
    (repo / "pyproject.toml").write_text(
        PYPROJECT.format(version="4.0.1"), encoding="utf-8"
    )
    (repo / "debian").mkdir()
    (repo / "debian" / "changelog").write_text(OLD_CHANGELOG, encoding="utf-8")
    (repo / "debian" / "scantpaper.install").write_text("x\n", encoding="utf-8")
    _commit(repo, "released 4.0.1-1")
    _git(repo, "tag", "debian/4.0.1-1")
    packaging = repo / "packaging" / "debian"
    packaging.mkdir(parents=True)
    (packaging / "control").write_text(NEW_CONTROL, encoding="utf-8")
    (packaging / "rules").write_text(NEW_RULES, encoding="utf-8")
    (packaging / "changelog").write_text(CHANGELOG_TEMPLATE, encoding="utf-8")
    _git(repo, "tag", "upstream/4.0.1")

    result = _run(repo, "--date", "2026-11-01")

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "pre-migration" in output
    assert "debian/scantpaper.install" in output


def test_source_date_epoch_sets_the_date(tmp_path: Path) -> None:
    """Use SOURCE_DATE_EPOCH when no date is given."""
    repo = _init_repo(tmp_path)
    moment = datetime.datetime(2026, 12, 24, 12, tzinfo=datetime.UTC)

    result = _run(
        repo,
        env={**os.environ, "SOURCE_DATE_EPOCH": str(int(moment.timestamp()))},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    changelog = (repo / "debian" / "changelog").read_text()
    assert "Thu, 24 Dec 2026 00:00:00 +0000" in changelog
