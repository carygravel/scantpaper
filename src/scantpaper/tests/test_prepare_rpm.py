"""Tests for the RPM spec renderer in dev/prepare_rpm.py."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="git is not available",
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PREPARE = REPO_ROOT / "dev" / "prepare_rpm.py"

TEMPLATE = """Name:           scantpaper
Version:        @VERSION@
Release:        @RELEASE@%{?dist}
Summary:        Test package

Source0:        scantpaper-%{version}.tar.gz

%changelog
@CHANGELOG@
* Sun Sep 20 2026 Test Packager <test@example.com> - 3.0.19-1
- Initial package
"""

PYPROJECT = """[project]
name = "scantpaper"
version = "{version}"
"""


def _git(
    repo: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run git in ``repo`` and return the completed process."""
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def _commit(
    repo: Path,
    message: str,
    date: str = "2026-10-18T12:00:00+00:00",
) -> None:
    """Stage everything and commit it with a fixed date."""
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_DATE": date,
    }
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", message, env=env)


def _init_repo(
    tmp_path: Path,
    *,
    version: str = "3.0.24",
    template: str = TEMPLATE,
) -> Path:
    """Create a small git repository with a tracked spec template."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Test Packager")
    _git(repo, "config", "user.email", "test@example.com")
    (repo / "pyproject.toml").write_text(
        PYPROJECT.format(version=version), encoding="utf-8"
    )
    (repo / "packaging").mkdir()
    (repo / "packaging" / "scantpaper.spec").write_text(template, encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "version.txt").write_text(version, encoding="utf-8")
    _commit(repo, "initial", "2026-10-17T12:00:00+00:00")
    return repo


def _run(
    repo: Path,
    *,
    template: Path | None = None,
    source_ref: str = "HEAD",
    spec_out: Path | None = None,
    sources_dir: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    """Run the renderer and return its result and output paths."""
    if template is None:
        template = repo / "packaging" / "scantpaper.spec"
    if spec_out is None:
        spec_out = repo.parent / "out" / "scantpaper.spec"
    if sources_dir is None:
        sources_dir = repo.parent / "sources"
    result = subprocess.run(
        [
            sys.executable,
            str(PREPARE),
            "--repo-root",
            str(repo),
            "--template",
            str(template),
            "--source-ref",
            source_ref,
            "--spec-out",
            str(spec_out),
            "--sources-dir",
            str(sources_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    return result, spec_out, sources_dir


def _head(repo: Path, *args: str) -> str:
    """Return stripped git output for ``args``."""
    return _git(repo, *args).stdout.strip()


def test_branch_build_renders_spec_and_archive(tmp_path: Path) -> None:
    """Render a branch commit with its version, count and snapshot entry."""
    repo = _init_repo(tmp_path)
    (repo / "src" / "marker.txt").write_text("second\n", encoding="utf-8")
    _commit(repo, "second")
    count = _head(repo, "rev-list", "--count", "HEAD")
    sha = _head(repo, "rev-parse", "--short", "HEAD")

    result, spec, sources = _run(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    text = spec.read_text(encoding="utf-8")
    assert "Version:        3.0.24" in text
    assert f"Release:        0.{count}.g{sha}%{{?dist}}" in text
    assert "Source0:        scantpaper-%{version}.tar.gz" in text
    assert "Epoch:" not in text
    assert "@VERSION@" not in text
    assert "@RELEASE@" not in text
    assert "@CHANGELOG@" not in text
    assert (
        f"* Sun Oct 18 2026 Test Packager <test@example.com> - 3.0.24-0.{count}.g{sha}"
    ) in text
    assert f"- Snapshot build from commit {sha}." in text
    assert "3.0.19-1" in text
    assert (sources / "scantpaper-3.0.24.tar.gz").is_file()


def test_tag_at_head_identifies_the_release(tmp_path: Path) -> None:
    """Render HEAD at a release tag with a release changelog entry."""
    repo = _init_repo(tmp_path)
    _git(repo, "tag", "v3.0.24")
    count = _head(repo, "rev-list", "--count", "HEAD")
    sha = _head(repo, "rev-parse", "--short", "HEAD")

    result, spec, _sources = _run(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    text = spec.read_text(encoding="utf-8")
    assert "Version:        3.0.24" in text
    assert f"Release:        0.{count}.g{sha}%{{?dist}}" in text
    assert (
        f"* Sat Oct 17 2026 Test Packager <test@example.com> - 3.0.24-0.{count}.g{sha}"
    ) in text
    assert "- Release 3.0.24." in text


def test_tag_version_mismatch_writes_nothing(tmp_path: Path) -> None:
    """Reject a tag whose version disagrees with pyproject.toml."""
    repo = _init_repo(tmp_path)
    _git(repo, "tag", "v4.0.0")

    result, spec, sources = _run(repo, source_ref="v4.0.0")

    assert result.returncode != 0
    assert "does not match" in (result.stdout + result.stderr).lower()
    assert not spec.exists()
    assert not (sources / "scantpaper-3.0.24.tar.gz").exists()


def test_source_ref_uses_tag_source_and_current_template(tmp_path: Path) -> None:
    """Render an older tag while reading the template from the worktree."""
    repo = _init_repo(tmp_path)
    _git(repo, "tag", "v3.0.24")
    (repo / "pyproject.toml").write_text(
        PYPROJECT.format(version="4.0.0"), encoding="utf-8"
    )
    (repo / "src" / "version.txt").write_text("4.0.0", encoding="utf-8")
    _commit(repo, "next release")
    with (repo / "packaging" / "scantpaper.spec").open("a") as template:
        template.write("# worktree marker\n")

    result, spec, sources = _run(repo, source_ref="v3.0.24")

    assert result.returncode == 0, result.stdout + result.stderr
    text = spec.read_text(encoding="utf-8")
    assert "Version:        3.0.24" in text
    assert "- Release 3.0.24." in text
    assert "# worktree marker" in text
    archive = sources / "scantpaper-3.0.24.tar.gz"
    with tarfile.open(archive, "r:gz") as tar:
        version_file = tar.extractfile("scantpaper-3.0.24/src/version.txt")
        assert version_file is not None
        assert version_file.read() == b"3.0.24"
        archived_template = tar.extractfile(
            "scantpaper-3.0.24/packaging/scantpaper.spec"
        )
        assert archived_template is not None
        assert "worktree marker" not in archived_template.read().decode()


def test_archive_excludes_dirty_and_untracked_files(tmp_path: Path) -> None:
    """Archive the commit, not the dirty worktree."""
    repo = _init_repo(tmp_path)
    (repo / "src" / "version.txt").write_text("dirty", encoding="utf-8")
    (repo / "src" / "untracked.txt").write_text("untracked", encoding="utf-8")

    result, _spec, sources = _run(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    with tarfile.open(sources / "scantpaper-3.0.24.tar.gz", "r:gz") as tar:
        names = tar.getnames()
        assert "scantpaper-3.0.24/src/version.txt" in names
        assert "scantpaper-3.0.24/src/untracked.txt" not in names
        tracked = tar.extractfile("scantpaper-3.0.24/src/version.txt")
        assert tracked is not None
        assert tracked.read() == b"3.0.24"


def test_changelog_date_is_locale_independent(tmp_path: Path) -> None:
    """Use English weekday and month names under a German locale."""
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "LANG": "de_DE.UTF-8",
        "LC_ALL": "de_DE.UTF-8",
        "LC_TIME": "de_DE.UTF-8",
    }

    result, spec, _sources = _run(repo, env=env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "* Sat Oct 17 2026 Test Packager" in spec.read_text(encoding="utf-8")


def test_shallow_repository_is_rejected(tmp_path: Path) -> None:
    """Fail without outputs when history is too shallow for a count."""
    repo = _init_repo(tmp_path)
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", repo.as_uri(), str(shallow)],
        check=True,
    )

    result, spec, sources = _run(shallow)

    assert result.returncode != 0
    assert "shallow" in (result.stdout + result.stderr).lower()
    assert not spec.exists()
    assert not (sources / "scantpaper-3.0.24.tar.gz").exists()


def test_missing_placeholder_writes_nothing(tmp_path: Path) -> None:
    """Fail without outputs when the template lacks a placeholder."""
    repo = _init_repo(tmp_path)
    (repo / "packaging" / "scantpaper.spec").write_text(
        TEMPLATE.replace("@CHANGELOG@\n", ""), encoding="utf-8"
    )

    result, spec, sources = _run(repo)

    assert result.returncode != 0
    assert "placeholder" in (result.stdout + result.stderr).lower()
    assert not spec.exists()
    assert not (sources / "scantpaper-3.0.24.tar.gz").exists()


def test_missing_historical_packager_writes_nothing(tmp_path: Path) -> None:
    """Fail without outputs when no older changelog entry supplies a name."""
    template = TEMPLATE.split("* Sun Sep 20", maxsplit=1)[0].rstrip() + "\n"
    repo = _init_repo(tmp_path, template=template)

    result, spec, sources = _run(repo)

    assert result.returncode != 0
    assert "packager" in (result.stdout + result.stderr).lower()
    assert not spec.exists()
    assert not (sources / "scantpaper-3.0.24.tar.gz").exists()
