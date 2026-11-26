"""Tests for joining approved catalogs into AppStream and desktop metadata."""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "dev"
JOIN_PATH = DEV_DIR / "join_metadata.py"
DOMAIN = "scantpaper"

METAINFO = """<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop">
  <id>org.example.desktop</id>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0+</project_license>
  <name translate="no">Example</name>
  <summary>English summary</summary>
  <description>
    <p>This is a long enough English paragraph to describe the example
      application for the validator.</p>
  </description>
  <launchable type="desktop-id">org.example.desktop</launchable>
  <url type="homepage">https://example.org</url>
  <developer id="org.example"><name translate="no">Example</name></developer>
  <content_rating type="oars-1.1" />
</component>
"""

DESKTOP = """[Desktop Entry]
Name=Example
Comment=English comment
Exec=example
Icon=example
Terminal=false
Type=Application
Categories=Graphics;Scanning;
Keywords=one;two;
"""


def _load_join() -> ModuleType:
    """Import the join helper under test."""
    spec = importlib.util.spec_from_file_location("join_metadata", str(JOIN_PATH))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["join_metadata"] = module
    spec.loader.exec_module(module)
    return module


JOIN = _load_join()
SYSTEM_ITS = next(
    (
        path
        for path in JOIN.ITS_SEARCH_PATHS
        if (path / "metainfo.its").is_file() and (path / "metainfo.loc").is_file()
    ),
    None,
)
SUMMARY_RE = re.compile(r'<summary(?: xml:lang="([^"]*)")?>(.*?)</summary>', re.DOTALL)
requires_system_its = pytest.mark.skipif(
    SYSTEM_ITS is None,
    reason="system metainfo ITS rules are not installed",
)
requires_appstreamcli = pytest.mark.skipif(
    shutil.which("appstreamcli") is None,
    reason="appstreamcli is not installed",
)
requires_desktop_file_validate = pytest.mark.skipif(
    shutil.which("desktop-file-validate") is None,
    reason="desktop-file-validate is not installed",
)


def _write_templates(tmp_path: Path) -> tuple[Path, Path]:
    """Write an English-only metainfo and desktop template."""
    metainfo = tmp_path / "org.example.metainfo.xml"
    desktop = tmp_path / "org.example.desktop"
    metainfo.write_text(METAINFO, encoding="utf-8")
    desktop.write_text(DESKTOP, encoding="utf-8")
    return metainfo, desktop


def _write_mo(mo_dir: Path, language: str, body: str) -> None:
    """Compile a catalog body into ``<mo_dir>/<language>/.../<domain>.mo``."""
    po = mo_dir.parent / f"{language}.po"
    po.write_text(
        'msgid ""\n'
        'msgstr ""\n'
        '"MIME-Version: 1.0\\n"\n'
        '"Content-Type: text/plain; charset=UTF-8\\n"\n'
        f'"Language: {language}\\n"\n'
        "\n" + body,
        encoding="utf-8",
    )
    target = mo_dir / language / "LC_MESSAGES" / f"{DOMAIN}.mo"
    target.parent.mkdir(parents=True)
    subprocess.run(["msgfmt", "-o", str(target), str(po)], check=True)


def _run_join(tmp_path: Path, mo_dir: Path, its_dir: Path | None = SYSTEM_ITS) -> Path:
    """Join a fixture tree and return the output directory."""
    metainfo, desktop = _write_templates(tmp_path)
    out_dir = tmp_path / "out"
    JOIN.join(
        JOIN.JoinConfig(
            mo_dir=mo_dir,
            out_dir=out_dir,
            metainfo=metainfo,
            desktop=desktop,
            its_dir=its_dir,
        )
    )
    return out_dir


def _metainfo_text(out_dir: Path) -> str:
    return (out_dir / "org.example.metainfo.xml").read_text(encoding="utf-8")


def _summaries(out_dir: Path) -> list[tuple[str | None, str]]:
    return [
        (language or None, body.strip())
        for language, body in SUMMARY_RE.findall(_metainfo_text(out_dir))
    ]


def _translated_summaries(out_dir: Path, language: str) -> list[str]:
    return [body for lang, body in _summaries(out_dir) if lang == language]


@requires_system_its
def test_approved_translation_is_joined(tmp_path: Path) -> None:
    """A filled catalog entry becomes an inline translation."""
    mo_dir = tmp_path / "locale"
    _write_mo(
        mo_dir,
        "de",
        'msgid "English summary"\n'
        'msgstr "Deutsche Zusammenfassung"\n\n'
        'msgid "English comment"\n'
        'msgstr "Deutscher Kommentar"\n',
    )

    out_dir = _run_join(tmp_path, mo_dir)

    translated = _translated_summaries(out_dir, "de")
    assert translated == ["Deutsche Zusammenfassung"]
    desktop = (out_dir / "org.example.desktop").read_text(encoding="utf-8")
    assert "Comment[de]=Deutscher Kommentar" in desktop


@requires_system_its
def test_unapproved_translation_is_absent(tmp_path: Path) -> None:
    """A blanked entry falls back to the English text."""
    mo_dir = tmp_path / "locale"
    _write_mo(
        mo_dir,
        "de",
        'msgid "English summary"\nmsgstr ""\n\nmsgid "English comment"\nmsgstr ""\n',
    )

    out_dir = _run_join(tmp_path, mo_dir)

    assert _translated_summaries(out_dir, "de") == []
    assert (None, "English summary") in _summaries(out_dir)
    desktop = (out_dir / "org.example.desktop").read_text(encoding="utf-8")
    assert "Comment[de]" not in desktop


@requires_system_its
def test_fuzzy_translation_is_absent(tmp_path: Path) -> None:
    """A fuzzy entry is not compiled into the .mo tree, so it is absent."""
    mo_dir = tmp_path / "locale"
    _write_mo(
        mo_dir,
        "de",
        "#, fuzzy\n"
        'msgid "English summary"\n'
        'msgstr "Deutsche Zusammenfassung"\n\n'
        "#, fuzzy\n"
        'msgid "English comment"\n'
        'msgstr "Deutscher Kommentar"\n',
    )

    out_dir = _run_join(tmp_path, mo_dir)

    assert _translated_summaries(out_dir, "de") == []
    desktop = (out_dir / "org.example.desktop").read_text(encoding="utf-8")
    assert "Comment[de]" not in desktop


@requires_system_its
def test_desktop_name_and_keywords_are_preserved(tmp_path: Path) -> None:
    """A catalog cannot translate the brand or the keyword list."""
    mo_dir = tmp_path / "locale"
    _write_mo(
        mo_dir,
        "de",
        'msgid "English comment"\n'
        'msgstr "Deutscher Kommentar"\n\n'
        'msgid "Example"\n'
        'msgstr "Beispiel"\n\n'
        'msgid "one;two;"\n'
        'msgstr "eins;zwei;"\n',
    )

    out_dir = _run_join(tmp_path, mo_dir)

    desktop = (out_dir / "org.example.desktop").read_text(encoding="utf-8")
    assert "Name=Example" in desktop
    assert "Keywords=one;two;" in desktop
    assert "Name[de]" not in desktop
    assert "Keywords[de]" not in desktop
    assert '<name translate="no">Example</name>' in _metainfo_text(out_dir)


@requires_system_its
def test_inline_markup_is_rejected(tmp_path: Path) -> None:
    """Description markup that msgfmt would escape is a hard error."""
    metainfo = tmp_path / "org.example.metainfo.xml"
    desktop = tmp_path / "org.example.desktop"
    metainfo.write_text(
        METAINFO.replace("<p>This is", "<p><em>This</em> is"),
        encoding="utf-8",
    )
    desktop.write_text(DESKTOP, encoding="utf-8")

    with pytest.raises(JOIN.JoinError, match=r"<em>"):
        JOIN.join(
            JOIN.JoinConfig(
                mo_dir=tmp_path / "locale",
                out_dir=tmp_path / "out",
                metainfo=metainfo,
                desktop=desktop,
                its_dir=SYSTEM_ITS,
            )
        )


def test_missing_system_its_rules_are_rejected(tmp_path: Path) -> None:
    """The join fails loudly when the AppStream ITS rules are absent."""
    metainfo, desktop = _write_templates(tmp_path)
    its_dir = tmp_path / "its"
    its_dir.mkdir()

    with pytest.raises(JOIN.JoinError, match="no metainfo ITS rules"):
        JOIN.join(
            JOIN.JoinConfig(
                mo_dir=tmp_path / "locale",
                out_dir=tmp_path / "out",
                metainfo=metainfo,
                desktop=desktop,
                its_dir=its_dir,
            )
        )


def test_missing_template_is_rejected(tmp_path: Path) -> None:
    """A missing metainfo or desktop template is a hard error."""
    _metainfo, desktop = _write_templates(tmp_path)
    with pytest.raises(JOIN.JoinError, match="does not exist"):
        JOIN.join(
            JOIN.JoinConfig(
                mo_dir=tmp_path / "locale",
                out_dir=tmp_path / "out",
                metainfo=tmp_path / "missing.xml",
                desktop=desktop,
                its_dir=SYSTEM_ITS,
            )
        )


@requires_system_its
def test_empty_mo_tree_writes_english_metadata(tmp_path: Path) -> None:
    """No compiled catalog means every string falls back to English."""
    mo_dir = tmp_path / "locale"
    mo_dir.mkdir()

    out_dir = _run_join(tmp_path, mo_dir)

    assert _translated_summaries(out_dir, "de") == []
    desktop = (out_dir / "org.example.desktop").read_text(encoding="utf-8")
    assert "Comment[" not in desktop


@requires_system_its
def test_msgunfmt_failure_is_reported(tmp_path: Path) -> None:
    """A corrupt compiled catalog is a hard error, not silence."""
    metainfo, desktop = _write_templates(tmp_path)
    mo_dir = tmp_path / "locale"
    target = mo_dir / "de" / "LC_MESSAGES" / f"{DOMAIN}.mo"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"not a message catalog")

    with pytest.raises(JOIN.JoinError, match="msgunfmt for de"):
        JOIN.join(
            JOIN.JoinConfig(
                mo_dir=mo_dir,
                out_dir=tmp_path / "out",
                metainfo=metainfo,
                desktop=desktop,
                its_dir=SYSTEM_ITS,
            )
        )


def test_msgfmt_failure_is_reported() -> None:
    """A failing gettext command becomes a JoinError with its label."""
    with pytest.raises(JOIN.JoinError, match="msgfmt --xml failed"):
        JOIN._run(["sh", "-c", "exit 3"], "msgfmt --xml")


def _run_tool(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


@requires_system_its
@requires_appstreamcli
def test_joined_metainfo_validates(tmp_path: Path) -> None:
    """The translated metainfo still passes appstreamcli."""
    mo_dir = tmp_path / "locale"
    _write_mo(
        mo_dir,
        "de",
        'msgid "English summary"\nmsgstr "Deutsche Zusammenfassung"\n',
    )

    out_dir = _run_join(tmp_path, mo_dir)

    result = _run_tool(
        [
            "appstreamcli",
            "validate",
            "--no-net",
            str(out_dir / "org.example.metainfo.xml"),
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr


@requires_system_its
@requires_desktop_file_validate
def test_joined_desktop_validates(tmp_path: Path) -> None:
    """The translated desktop entry still passes desktop-file-validate."""
    mo_dir = tmp_path / "locale"
    _write_mo(
        mo_dir,
        "de",
        'msgid "English comment"\nmsgstr "Deutscher Kommentar"\n',
    )

    out_dir = _run_join(tmp_path, mo_dir)

    result = _run_tool(["desktop-file-validate", str(out_dir / "org.example.desktop")])
    assert result.returncode == 0, result.stdout + result.stderr
