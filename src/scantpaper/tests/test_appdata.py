"""Tests for AppStream metadata files."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
METAINFO = REPO_ROOT / "org.scantpaper.desktop.metainfo.xml"
DESKTOP = REPO_ROOT / "org.scantpaper.desktop"

DESCRIPTION_RE = re.compile(r"<description>(.*?)</description>", re.DOTALL)
TAG_RE = re.compile(r"<\s*([A-Za-z][\w.:-]*)")
BLOCK_TAGS = frozenset({"li", "ol", "p", "ul"})


def test_appstream_validate() -> None:
    """Validate AppStream metadata with appstreamcli."""
    result = subprocess.run(
        ["appstreamcli", "validate", "--no-net", str(METAINFO)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_source_metainfo_has_no_inline_translation() -> None:
    """The source metainfo carries only the English text."""
    text = METAINFO.read_text(encoding="utf-8")
    assert "xml:lang" not in text, f"{METAINFO.name} has an inline xml:lang"


def test_brand_and_developer_name_are_not_translated() -> None:
    """The brand and developer name are marked untranslatable."""
    text = METAINFO.read_text(encoding="utf-8")
    assert '<name translate="no">scantpaper</name>' in text, (
        f'{METAINFO.name} does not mark the brand name translate="no"'
    )
    assert re.search(r'<developer\b[^>]*>\s*<name translate="no">', text), (
        f'{METAINFO.name} does not mark the developer name translate="no"'
    )


def test_description_has_no_inline_markup() -> None:
    """The description uses paragraphs only, so gettext can join it."""
    text = METAINFO.read_text(encoding="utf-8")
    match = DESCRIPTION_RE.search(text)
    assert match is not None, f"{METAINFO.name} has no description"
    for tag_match in TAG_RE.finditer(match.group(1)):
        tag = tag_match.group(1)
        assert tag in BLOCK_TAGS, (
            f"{METAINFO.name} description has inline <{tag}> markup"
        )


def test_source_desktop_entry_has_no_localized_key() -> None:
    """The source desktop entry carries only the English text."""
    for line in DESKTOP.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith(("#", "[")):
            continue
        key = line.split("=", 1)[0]
        assert "[" not in key, f"{DESKTOP.name} has a localized key: {key}"
