"""Tests that the RPM specs are build-time templates."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

SPECS = (
    REPO_ROOT / "packaging" / "fedora" / "scantpaper.spec",
    REPO_ROOT / "packaging" / "opensuse" / "scantpaper.spec",
)


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
