"""Tests for the release-preparation script dev/release.py."""

from __future__ import annotations

import datetime
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
RELEASE = REPO_ROOT / "dev" / "release.py"

CHANGELOG = """## 3.0.22 (unreleased)

* A change.

## 3.0.21 (2026-10-04)

* Older.
"""

PYPROJECT = """[project]
name = "scantpaper"
version = "3.0.21"
dependencies = ["img2pdf"]

[tool.ruff]
target-version = "py310"
"""

METAINFO = """<?xml version="1.0" encoding="UTF-8" ?>
<component type="desktop">
  <id>org.scantpaper.desktop</id>
  <releases>
    <release version="3.0.21" date="2026-10-04" />
  </releases>
</component>
"""


def _write(
    tmp_path: Path,
    *,
    changelog: str = CHANGELOG,
    pyproject: str = PYPROJECT,
    metainfo: str = METAINFO,
) -> Path:
    """Write a minimal release tree and return its root."""
    (tmp_path / "changelog.md").write_text(changelog, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    (tmp_path / "org.scantpaper.desktop.metainfo.xml").write_text(
        metainfo, encoding="utf-8"
    )
    return tmp_path


def _run(
    root: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run dev/release.py against ``root`` and capture its output."""
    return subprocess.run(
        [sys.executable, str(RELEASE), "--root", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _unchanged(root: Path) -> bool:
    """Return True if the three files still hold their original contents."""
    return (
        (root / "changelog.md").read_text(encoding="utf-8") == CHANGELOG
        and (root / "pyproject.toml").read_text(encoding="utf-8") == PYPROJECT
        and (root / "org.scantpaper.desktop.metainfo.xml").read_text(encoding="utf-8")
        == METAINFO
    )


def test_version_taken_from_changelog(tmp_path: Path) -> None:
    """Use the changelog's (unreleased) heading as the version."""
    root = _write(tmp_path)
    result = _run(root, "--date", "2026-10-10")
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'version = "3.0.22"' in (root / "pyproject.toml").read_text(encoding="utf-8")


def test_version_override_matches(tmp_path: Path) -> None:
    """Accept a --version that matches the changelog."""
    root = _write(tmp_path)
    result = _run(root, "--version", "3.0.22", "--date", "2026-10-10")
    assert result.returncode == 0, result.stdout + result.stderr


def test_version_override_mismatch_writes_nothing(tmp_path: Path) -> None:
    """Reject a --version that disagrees, writing nothing."""
    root = _write(tmp_path)
    result = _run(root, "--version", "3.0.23", "--date", "2026-10-10")
    assert result.returncode == 1
    assert "--version" in result.stdout
    assert _unchanged(root)


def test_no_unreleased_heading_writes_nothing(tmp_path: Path) -> None:
    """Reject a changelog with no (unreleased) heading."""
    root = _write(tmp_path, changelog="## 3.0.21 (2026-10-04)\n\n* Older.\n")
    before = (root / "changelog.md").read_text(encoding="utf-8")
    result = _run(root, "--date", "2026-10-10")
    assert result.returncode == 1
    assert "unreleased" in result.stdout
    assert (root / "changelog.md").read_text(encoding="utf-8") == before
    assert 'version = "3.0.21"' in (root / "pyproject.toml").read_text(encoding="utf-8")


def test_changelog_and_metainfo_share_the_date(tmp_path: Path) -> None:
    """Write one date to both the changelog and metainfo."""
    root = _write(tmp_path)
    result = _run(root, "--date", "2026-10-10")
    assert result.returncode == 0, result.stdout + result.stderr
    changelog = (root / "changelog.md").read_text(encoding="utf-8")
    metainfo = (root / "org.scantpaper.desktop.metainfo.xml").read_text(
        encoding="utf-8"
    )
    assert "## 3.0.22 (2026-10-10)" in changelog
    assert '<release version="3.0.22" date="2026-10-10" />' in metainfo


def test_date_override_applies_to_both(tmp_path: Path) -> None:
    """Apply --date to both files."""
    root = _write(tmp_path)
    result = _run(root, "--date", "2026-10-04")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "## 3.0.22 (2026-10-04)" in (root / "changelog.md").read_text(
        encoding="utf-8"
    )
    assert '<release version="3.0.22" date="2026-10-04" />' in (
        root / "org.scantpaper.desktop.metainfo.xml"
    ).read_text(encoding="utf-8")


def test_source_date_epoch_is_honoured(tmp_path: Path) -> None:
    """Fall back to SOURCE_DATE_EPOCH when --date is absent."""
    root = _write(tmp_path)
    epoch = 1_700_000_000
    expected = datetime.datetime.fromtimestamp(
        epoch, tz=datetime.timezone.utc
    ).strftime("%Y-%m-%d")
    env = {**os.environ, "SOURCE_DATE_EPOCH": str(epoch)}
    result = _run(root, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"## 3.0.22 ({expected})" in (root / "changelog.md").read_text(
        encoding="utf-8"
    )


def test_stamp_changelog_preserves_bullets(tmp_path: Path) -> None:
    """Date only the heading, leaving bullets unchanged."""
    root = _write(tmp_path)
    result = _run(root, "--date", "2026-10-10")
    assert result.returncode == 0, result.stdout + result.stderr
    expected = CHANGELOG.replace("## 3.0.22 (unreleased)", "## 3.0.22 (2026-10-10)")
    assert (root / "changelog.md").read_text(encoding="utf-8") == expected


def test_bump_pyproject_preserves_other_lines(tmp_path: Path) -> None:
    """Change only the version line in pyproject.toml."""
    root = _write(tmp_path)
    result = _run(root, "--date", "2026-10-10")
    assert result.returncode == 0, result.stdout + result.stderr
    expected = PYPROJECT.replace('version = "3.0.21"', 'version = "3.0.22"')
    assert (root / "pyproject.toml").read_text(encoding="utf-8") == expected


def test_metainfo_entry_is_first_and_older_unchanged(tmp_path: Path) -> None:
    """Insert the new release above older entries."""
    root = _write(tmp_path)
    result = _run(root, "--date", "2026-10-10")
    assert result.returncode == 0, result.stdout + result.stderr
    expected = METAINFO.replace(
        "  <releases>\n",
        '  <releases>\n    <release version="3.0.22" date="2026-10-10" />\n',
    )
    assert (root / "org.scantpaper.desktop.metainfo.xml").read_text(
        encoding="utf-8"
    ) == expected


def test_all_or_nothing_on_unparsable_metainfo(tmp_path: Path) -> None:
    """Leave every file untouched when one is invalid."""
    root = _write(
        tmp_path,
        metainfo="<component><id>org.scantpaper.desktop</id></component>\n",
    )
    metainfo_before = (root / "org.scantpaper.desktop.metainfo.xml").read_text(
        encoding="utf-8"
    )
    result = _run(root, "--date", "2026-10-10")
    assert result.returncode == 1
    assert "<releases>" in result.stdout
    assert (root / "changelog.md").read_text(encoding="utf-8") == CHANGELOG
    assert (root / "pyproject.toml").read_text(encoding="utf-8") == PYPROJECT
    assert (root / "org.scantpaper.desktop.metainfo.xml").read_text(
        encoding="utf-8"
    ) == metainfo_before


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    """Report the changes without writing any file."""
    root = _write(tmp_path)
    result = _run(root, "--date", "2026-10-10", "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "3.0.22" in result.stdout
    assert _unchanged(root)


def test_invalid_date_writes_nothing(tmp_path: Path) -> None:
    """Reject a malformed --date, writing nothing."""
    root = _write(tmp_path)
    result = _run(root, "--date", "10-10-2026")
    assert result.returncode == 1
    assert _unchanged(root)
