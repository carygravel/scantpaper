"""Tests for the published release assets and release page text."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
BODY = REPO_ROOT / ".github" / "release-notes.md"
README = REPO_ROOT / "README.md"
OPENSUE_README = REPO_ROOT / "packaging" / "opensuse" / "README.md"
RELEASE_WORKFLOWS = (
    "test.yml",
    "deb.yml",
    "fedora.yml",
    "opensuse.yml",
    "opensuse-tumbleweed.yml",
)


def _workflow(name: str) -> str:
    """Return a workflow file's text."""
    return (WORKFLOWS / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("workflow", "target", "artifact_name"),
    [
        (
            "fedora.yml",
            "fedora-${{ matrix.fedora }}",
            "scantpaper-fedora-${{ matrix.fedora }}",
        ),
        (
            "opensuse.yml",
            "opensuse-leap-16.0",
            "scantpaper-opensuse-leap16",
        ),
        (
            "opensuse-tumbleweed.yml",
            "opensuse-tumbleweed",
            "scantpaper-opensuse-tumbleweed",
        ),
    ],
)
def test_rpm_workflow_builds_and_releases_a_bundle(
    workflow: str, target: str, artifact_name: str
) -> None:
    """Build one archive per target and keep the RPM CI artifact."""
    text = _workflow(workflow)

    assert "python3 dev/make_release_bundle.py" in text
    assert f"--target {target}" in text
    assert "--input artifacts" in text
    assert "--output dist" in text
    assert "files: dist/*.tar.gz" in text
    assert "files: artifacts/*.rpm" not in text
    assert "if: github.ref_type == 'tag'" in text
    assert f"name: {artifact_name}" in text
    assert "path: artifacts/*.rpm" in text


def test_release_body_names_every_target() -> None:
    """Name every archive and the single-file alternatives."""
    text = BODY.read_text(encoding="utf-8")

    for target in (
        "fedora-43",
        "fedora-44",
        "opensuse-leap-16.0",
        "opensuse-tumbleweed",
    ):
        assert target in text
    assert ".deb" in text
    assert ".whl" in text
    assert "--allow-unsigned-rpm" in text
    assert re.search(r"scantpaper-\d+\.\d+", text) is None


@pytest.mark.parametrize("workflow", RELEASE_WORKFLOWS)
def test_every_release_step_uses_the_body(workflow: str) -> None:
    """Point every tag release at the checked-in body."""
    text = _workflow(workflow)

    assert text.count("body_path: .github/release-notes.md") == 1
    assert "if: github.ref_type == 'tag'" in text


def test_docs_describe_the_archive_workflow() -> None:
    """Describe the archives and drop the old Leap suffix rule."""
    readme = README.read_text(encoding="utf-8")

    assert "tar -xf scantpaper-*-fedora-43.tar.gz" in readme
    assert "tar -xf scantpaper-*-opensuse-leap-16.0.tar.gz" in readme
    assert "tar -xf scantpaper-*-opensuse-tumbleweed.tar.gz" in readme
    assert "the ones with the `.lp160.1` release" not in readme
    assert "the files without the `.lp160.1` release" not in readme

    packaging_readme = OPENSUE_README.read_text(encoding="utf-8")
    assert "dev/make_release_bundle.py" in packaging_readme
    assert "collect-runtime" in packaging_readme
    assert "the release assets do not collide" not in packaging_readme
