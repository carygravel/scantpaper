"""Tests that the packaging files are build-time templates."""

from __future__ import annotations

import re
import stat
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

SPECS = (
    REPO_ROOT / "packaging" / "fedora" / "scantpaper.spec",
    REPO_ROOT / "packaging" / "opensuse" / "scantpaper.spec",
)

DEBIAN = REPO_ROOT / "packaging" / "debian"


def test_specs_are_rendered_from_templates() -> None:
    """Require placeholders instead of a version fixed in the spec."""
    for spec in SPECS:
        text = spec.read_text(encoding="utf-8")
        assert "Version:        @VERSION@" in text, spec
        assert "Release:        @RELEASE@%{?dist}" in text, spec
        assert "Source0:        scantpaper-%{version}.tar.gz" in text, spec
        assert re.search(r"(?m)^%changelog\n@CHANGELOG@$", text), spec
        assert not re.search(r"(?m)^Version:[ \t]+(?!@VERSION@)\S", text), spec
        assert not re.search(r"(?m)^Release:[ \t]+(?!@RELEASE@)\S", text), spec


def test_specs_do_not_set_epoch() -> None:
    """Keep the upstream release ordering without an Epoch."""
    for spec in SPECS:
        text = spec.read_text(encoding="utf-8")
        assert not re.search(r"(?m)^Epoch:", text), spec


def test_debian_changelog_is_rendered_from_a_template() -> None:
    """Require placeholders instead of a version fixed in the changelog."""
    text = (DEBIAN / "changelog").read_text(encoding="utf-8")
    assert "scantpaper (@VERSION@) unstable; urgency=medium" in text
    assert "@TEXT@" in text
    assert "@DATE@" in text
    assert not re.search(r"\d+(?:\.\d+)+", text)


def test_debian_rules_is_executable() -> None:
    """Record the executable bit Debian policy requires for debian/rules."""
    mode = (DEBIAN / "rules").stat().st_mode
    assert mode & stat.S_IXUSR
