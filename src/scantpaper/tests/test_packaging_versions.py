"""Tests that the packaging files are build-time templates."""

from __future__ import annotations

import re
import stat
from pathlib import Path
from typing import cast

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


def test_fedora_spec_requires_gtk_and_cairo_typelibs() -> None:
    """Require the packages that provide the Gtk and cairo typelibs."""
    text = (REPO_ROOT / "packaging" / "fedora" / "scantpaper.spec").read_text(
        encoding="utf-8"
    )
    assert re.search(r"(?m)^Requires:\s+gtk4$", text)
    assert re.search(r"(?m)^Requires:\s+gobject-introspection$", text)


def test_opensuse_spec_has_tumbleweed_and_leap_dependency_branches() -> None:
    """Keep the Tumbleweed and Leap dependency sets separate."""
    text = (REPO_ROOT / "packaging" / "opensuse" / "scantpaper.spec").read_text(
        encoding="utf-8"
    )
    condition = "%if 0%{?suse_version} >= 1699"
    assert text.count(condition) == 4
    assert text.count("%else") == 4
    assert text.count("%endif") == 4
    for name in (
        "python3-devel",
        "python3-gobject",
        "python3-tesserocr",
        "python3-ocrmypdf",
        "python3-img2pdf",
        "python3-sane",
        "python3-python-iso639",
        "python3-pikepdf",
        "python3-typing_extensions",
    ):
        assert f"BuildRequires:  {name}" in text or f"Requires:  {name}" in text
    for name in (
        "python313-devel",
        "python313-gobject",
        "python313-tesserocr",
        "python313-ocrmypdf",
        "python313-img2pdf",
        "python313-sane",
        "python313-python-iso639",
        "python313-pikepdf",
        "python313-typing_extensions",
    ):
        assert f"BuildRequires:  {name}" in text or f"Requires:  {name}" in text
    assert not re.search(r"(?m)^[ \t]*(?:Requires|BuildRequires):.*python3dist\(", text)


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


def _field(text: str, name: str) -> str:
    """Return the continuation lines of a Debian control field."""
    match = re.search(rf"(?ms)^{name}:\s*(.*?)(?=^\S|\Z)", text)
    assert match is not None, name
    return cast("str", match.group(1))


def test_autopkgtest_declares_git_but_runtime_does_not() -> None:
    """Debian can run the git-dependent tests without shipping git."""
    tests_control = (DEBIAN / "tests" / "control").read_text(encoding="utf-8")
    runtime_control = (DEBIAN / "control").read_text(encoding="utf-8")

    assert re.search(r"(?m)^\s*git,\s*$", _field(tests_control, "Depends"))
    assert not re.search(r"(?m)^\s*git(?:,|\s*$)", _field(runtime_control, "Depends"))
