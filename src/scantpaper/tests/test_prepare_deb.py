"""Tests for the Debian packaging renderer in dev/prepare_deb.py."""

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
PREPARE = REPO_ROOT / "dev" / "prepare_deb.py"

CHANGELOG = """scantpaper (@VERSION@) unstable; urgency=medium

  * @TEXT@

 -- Test Packager <test@example.com>  @DATE@
"""

RULES = """#!/usr/bin/make -f

%:
\tdh $@ --with python3 --buildsystem=pybuild
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
    version: str = "4.0.1",
    template: str = CHANGELOG,
) -> Path:
    """Create a small git repository with a tracked packaging template."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Test Packager")
    _git(repo, "config", "user.email", "test@example.com")
    (repo / "pyproject.toml").write_text(
        PYPROJECT.format(version=version), encoding="utf-8"
    )
    packaging = repo / "packaging" / "debian"
    packaging.mkdir(parents=True)
    (packaging / "changelog").write_text(template, encoding="utf-8")
    (packaging / "control").write_text("Source: scantpaper\n", encoding="utf-8")
    rules = packaging / "rules"
    rules.write_text(RULES, encoding="utf-8")
    rules.chmod(0o755)
    (packaging / "README.md").write_text("template docs\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "version.txt").write_text(version, encoding="utf-8")
    _commit(repo, "initial", "2026-10-17T12:00:00+00:00")
    return repo


def _run(
    repo: Path,
    *,
    source_ref: str = "HEAD",
    build_root: Path | None = None,
    template_dir: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    """Run the renderer and return its result and build root."""
    if build_root is None:
        build_root = repo.parent / "out" / "deb"
    if template_dir is None:
        template_dir = repo / "packaging" / "debian"
    result = subprocess.run(
        [
            sys.executable,
            str(PREPARE),
            "--repo-root",
            str(repo),
            "--template-dir",
            str(template_dir),
            "--source-ref",
            source_ref,
            "--build-root",
            str(build_root),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    return result, build_root


def _head(repo: Path, *args: str) -> str:
    """Return stripped git output for ``args``."""
    return _git(repo, *args).stdout.strip()


def _assert_no_tree(build_root: Path) -> None:
    """Assert that no rendered tree exists under ``build_root``."""
    assert not build_root.exists() or not any(build_root.iterdir())


def test_branch_build_renders_tree_and_version(tmp_path: Path) -> None:
    """Render a branch commit with a snapshot changelog entry."""
    repo = _init_repo(tmp_path)
    (repo / "src" / "marker.txt").write_text("second\n", encoding="utf-8")
    _commit(repo, "second")
    count = _head(repo, "rev-list", "--count", "HEAD")
    sha = _head(repo, "rev-parse", "--short", "HEAD")
    version = f"4.0.1-0.{count}.g{sha}"

    result, build_root = _run(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == version
    tree = build_root / f"scantpaper-{version}"
    changelog = (tree / "debian" / "changelog").read_text(encoding="utf-8")
    assert f"scantpaper ({version}) unstable; urgency=medium" in changelog
    assert f"Snapshot build from commit {sha}." in changelog
    assert "Sun, 18 Oct 2026 12:00:00 +0000" in changelog
    assert "@VERSION@" not in changelog
    assert "@TEXT@" not in changelog
    assert "@DATE@" not in changelog
    assert (tree / "src" / "marker.txt").read_text(encoding="utf-8") == "second\n"


def test_tag_at_head_identifies_the_release(tmp_path: Path) -> None:
    """Render HEAD at a release tag with a release changelog entry."""
    repo = _init_repo(tmp_path)
    _git(repo, "tag", "v4.0.1")
    count = _head(repo, "rev-list", "--count", "HEAD")
    sha = _head(repo, "rev-parse", "--short", "HEAD")
    version = f"4.0.1-0.{count}.g{sha}"

    result, build_root = _run(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == version
    changelog = (
        build_root / f"scantpaper-{version}" / "debian" / "changelog"
    ).read_text(encoding="utf-8")
    assert "Release 4.0.1." in changelog
    assert "Sat, 17 Oct 2026 12:00:00 +0000" in changelog


def test_same_commit_renders_same_version(tmp_path: Path) -> None:
    """Give one commit one version whether or not its tag exists."""
    repo = _init_repo(tmp_path)

    untagged, _ = _run(repo, build_root=tmp_path / "untagged")
    _git(repo, "tag", "v4.0.1")
    tagged, _ = _run(repo, build_root=tmp_path / "tagged")

    assert untagged.returncode == 0, untagged.stdout + untagged.stderr
    assert tagged.returncode == 0, tagged.stdout + tagged.stderr
    assert untagged.stdout.strip() == tagged.stdout.strip()


def test_tag_version_mismatch_writes_nothing(tmp_path: Path) -> None:
    """Reject a tag whose version disagrees with pyproject.toml."""
    repo = _init_repo(tmp_path)
    _git(repo, "tag", "v4.0.0")

    result, build_root = _run(repo, source_ref="v4.0.0")

    assert result.returncode != 0
    assert "does not match" in (result.stdout + result.stderr).lower()
    _assert_no_tree(build_root)


def test_source_ref_uses_tag_tree_and_current_template(tmp_path: Path) -> None:
    """Render an older tag while reading the template from the worktree."""
    repo = _init_repo(tmp_path)
    _git(repo, "tag", "v4.0.1")
    (repo / "pyproject.toml").write_text(
        PYPROJECT.format(version="4.0.2"), encoding="utf-8"
    )
    (repo / "src" / "version.txt").write_text("4.0.2", encoding="utf-8")
    _commit(repo, "next release")
    changelog_template = repo / "packaging" / "debian" / "changelog"
    with changelog_template.open("a") as template:
        template.write("# worktree marker\n")

    result, build_root = _run(repo, source_ref="v4.0.1")

    assert result.returncode == 0, result.stdout + result.stderr
    version = result.stdout.strip()
    assert version.startswith("4.0.1-0.")
    tree = build_root / f"scantpaper-{version}"
    assert "4.0.1" in (tree / "pyproject.toml").read_text(encoding="utf-8")
    assert (tree / "src" / "version.txt").read_text(encoding="utf-8") == "4.0.1"
    changelog = (tree / "debian" / "changelog").read_text(encoding="utf-8")
    assert "# worktree marker" in changelog


def test_archive_excludes_dirty_and_untracked_files(tmp_path: Path) -> None:
    """Render the commit, not the dirty worktree."""
    repo = _init_repo(tmp_path)
    (repo / "src" / "version.txt").write_text("dirty", encoding="utf-8")
    (repo / "src" / "untracked.txt").write_text("untracked", encoding="utf-8")

    result, build_root = _run(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    tree = build_root / f"scantpaper-{result.stdout.strip()}"
    assert (tree / "src" / "version.txt").read_text(encoding="utf-8") == "4.0.1"
    assert not (tree / "src" / "untracked.txt").exists()


def test_changelog_date_is_locale_independent(tmp_path: Path) -> None:
    """Use English weekday and month names under a German locale."""
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "LANG": "de_DE.UTF-8",
        "LC_ALL": "de_DE.UTF-8",
        "LC_TIME": "de_DE.UTF-8",
    }

    result, build_root = _run(repo, env=env)

    assert result.returncode == 0, result.stdout + result.stderr
    changelog = (
        build_root / f"scantpaper-{result.stdout.strip()}" / "debian" / "changelog"
    ).read_text(encoding="utf-8")
    assert "Sat, 17 Oct 2026 12:00:00 +0000" in changelog


def test_shallow_repository_is_rejected(tmp_path: Path) -> None:
    """Fail without output when history is too shallow for a count."""
    repo = _init_repo(tmp_path)
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", repo.as_uri(), str(shallow)],
        check=True,
    )

    result, build_root = _run(shallow)

    assert result.returncode != 0
    assert "shallow" in (result.stdout + result.stderr).lower()
    _assert_no_tree(build_root)


def test_missing_placeholder_writes_nothing(tmp_path: Path) -> None:
    """Fail without output when the template lacks a placeholder."""
    repo = _init_repo(tmp_path, template=CHANGELOG.replace("@DATE@", "date"))

    result, build_root = _run(repo)

    assert result.returncode != 0
    assert "placeholder" in (result.stdout + result.stderr).lower()
    _assert_no_tree(build_root)


def test_rendered_tree_has_native_files_and_executable_rules(tmp_path: Path) -> None:
    """Copy the packaging files verbatim and keep rules executable."""
    repo = _init_repo(tmp_path)

    result, build_root = _run(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    debian = build_root / f"scantpaper-{result.stdout.strip()}" / "debian"
    files = {path.name for path in debian.iterdir() if path.is_file()}
    assert files == {"changelog", "control", "rules"}
    assert not (debian / "README.md").exists()
    assert os.access(debian / "rules", os.X_OK)


def test_failed_render_keeps_the_previous_tree(tmp_path: Path) -> None:
    """Leave the last good tree in place when a later render fails."""
    repo = _init_repo(tmp_path)
    first, build_root = _run(repo)
    assert first.returncode == 0, first.stdout + first.stderr
    tree = build_root / f"scantpaper-{first.stdout.strip()}"
    changelog = tree / "debian" / "changelog"
    before = changelog.read_text(encoding="utf-8")
    template = repo / "packaging" / "debian" / "changelog"
    template.write_text(CHANGELOG.replace("@DATE@", "date"), encoding="utf-8")

    second, _build_root = _run(repo)

    assert second.returncode != 0
    assert changelog.read_text(encoding="utf-8") == before
    assert (tree / "src" / "version.txt").read_text(encoding="utf-8") == "4.0.1"
