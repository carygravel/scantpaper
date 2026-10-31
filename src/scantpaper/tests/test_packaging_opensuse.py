"""Tests for the openSUSE build driver and its Tumbleweed target."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BUILD = REPO_ROOT / "packaging" / "opensuse" / "build.sh"
SANE = REPO_ROOT / "packaging" / "opensuse" / "python313-sane.spec"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "opensuse-tumbleweed.yml"
README = REPO_ROOT / "README.md"


def _run(target: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the build driver with a target and capture its trace."""
    env = dict(os.environ, TARGET=target)
    return subprocess.run(
        ["bash", "-x", str(BUILD), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_unknown_target_is_rejected() -> None:
    """Reject a target before setup or a build starts."""
    result = _run("bogus", "build", "sane")
    assert result.returncode == 1
    assert "unknown target" in result.stderr
    assert "bogus" in result.stderr


def test_target_arrays_are_distinct() -> None:
    """Keep the Leap dependency chain out of the Tumbleweed target."""
    leap = _run("leap16").stderr
    tumbleweed = _run("tumbleweed").stderr
    assert "ORDER=(sane scantpaper)" in tumbleweed
    assert "RUNTIME=(sane scantpaper)" in tumbleweed
    assert "ORDER=(sane scantpaper)" not in leap
    assert "cysignals" in leap
    assert "ocrmypdf" in leap


def test_dist_suffix_is_target_specific() -> None:
    """Apply the Leap suffix only to the Leap target."""
    text = BUILD.read_text(encoding="utf-8")
    leap_branch = 'if [ "$TARGET" = leap16 ]; then'
    assert leap_branch in text
    assert "%dist .lp160.1" in text
    assert "rm -f /usr/lib/rpm/macros.d/macros.dist" in text
    assert text.index(leap_branch) < text.index("%dist .lp160.1")


def test_sane_spec_follows_the_python_flavor() -> None:
    """Build the patched sane for the target's default Python flavor."""
    text = SANE.read_text(encoding="utf-8")
    assert "%{!?pyflavor:%define pyflavor 313}" in text
    assert "Name:           python%{pyflavor}-sane" in text
    assert "BuildRequires:  python%{pyflavor}-devel" in text
    assert "Requires:       python%{pyflavor}-numpy" in text


def test_sane_spec_preserves_tumbleweed_capabilities() -> None:
    """Keep the distribution names available when replacing its package."""
    text = SANE.read_text(encoding="utf-8")
    assert "Provides:       python3-sane = %{version}" in text
    assert "Provides:       python3dist(python-sane) = %{version}" in text


def test_sane_spec_sorts_above_the_same_distro_version() -> None:
    """Use the trailing segment that wins over the distribution build."""
    text = SANE.read_text(encoding="utf-8")
    assert "%define pkg_version 2.9.2" in text
    assert "Version:        %{pkg_version}.0" in text


def test_tumbleweed_workflow_uses_the_standard_triggers() -> None:
    """Match the triggers of the other package builds."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "on:\n  push:\n  pull_request:\n  workflow_dispatch:" in text
    assert "source_ref:" in text


def test_tumbleweed_workflow_builds_the_distribution_set() -> None:
    """Build only the patched sane and ScantPaper on Tumbleweed."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "image: opensuse/tumbleweed:latest" in text
    assert "TARGET=tumbleweed bash packaging/opensuse/build.sh build sane" in text
    assert "TARGET=tumbleweed bash packaging/opensuse/build.sh build scantpaper" in text
    assert "name: scantpaper-opensuse-tumbleweed" in text
    assert "Verify the installed version matches the release tag" in text


def test_tumbleweed_workflow_has_a_seeded_clean_room() -> None:
    """Exercise replacing the distribution python-sane without an update."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "matrix.scenario == 'seeded'" in text
    assert "zypper -n --gpg-auto-import-keys install python3-sane" in text
    assert "Survive a subsequent update" not in text


def test_readme_documents_the_tumbleweed_artifact() -> None:
    """Tell Tumbleweed users what is rebuilt and what is unavailable."""
    text = README.read_text(encoding="utf-8")
    assert "##### Tumbleweed" in text
    assert "patched `python-sane`" in text
    assert "tiff2ps" in text
