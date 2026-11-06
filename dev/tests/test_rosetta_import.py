"""Tests for the offline Rosetta import in dev/rosetta_import.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import polib

if TYPE_CHECKING:
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "dev"
IMPORT_PATH = DEV_DIR / "rosetta_import.py"

sys.path.insert(0, str(DEV_DIR))


def _load_import() -> ModuleType:
    """Import dev/rosetta_import.py."""
    spec = importlib.util.spec_from_file_location("rosetta_import", str(IMPORT_PATH))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["rosetta_import"] = module
    spec.loader.exec_module(module)
    return module


ROSETTA = _load_import()


def _write(path: Path, entries: list[tuple[str, str, bool]]) -> None:
    """Write a catalog with (msgid, msgstr, fuzzy) entries."""
    po = polib.POFile()
    po.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
    }
    for msgid, msgstr, fuzzy in entries:
        entry = polib.POEntry(msgid=msgid, msgstr=msgstr)
        if fuzzy:
            entry.flags.append("fuzzy")
        po.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(path))


def _fixture(
    tmp_path: Path, export_entries: list[tuple[str, str, bool]]
) -> tuple[Path, Path, Path]:
    """Build a template, a fuzzy catalog and a downloaded export."""
    src = tmp_path / "po" / "scantpaper"
    pot = src / "scantpaper.pot"
    catalog = src / "de.po"
    export = tmp_path / "de.po"
    _write(pot, [("Delete", "", False), ("Open", "", False)])
    _write(catalog, [("Delete", "Altes Löschen", True)])
    _write(export, export_entries)
    return src, pot, export


def _run(src: Path, pot: Path, export: Path, *extra: str) -> int:
    """Run the import command."""
    result = ROSETTA.main(
        [
            "--pot",
            str(pot),
            "--src",
            str(src),
            "--import",
            str(export),
            *extra,
        ]
    )
    return int(result)


def test_valid_export_merges_and_clears_fuzzy(tmp_path: Path) -> None:
    """A confirmed export replaces the fuzzy text and adds a missing message."""
    src, pot, export = _fixture(
        tmp_path,
        [("Delete", "Löschen", False), ("Open", "Öffnen", False)],
    )
    assert _run(src, pot, export, "--apply") == 0

    catalog = polib.pofile(str(src / "de.po"))
    delete = catalog.find("Delete")
    opened = catalog.find("Open")
    assert delete is not None
    assert opened is not None
    assert delete.msgstr == "Löschen"
    assert "fuzzy" not in delete.flags
    assert opened.msgstr == "Öffnen"


def test_mismatched_template_is_rejected(tmp_path: Path) -> None:
    """An export with a msgid outside the template is not merged."""
    src, pot, export = _fixture(tmp_path, [("Unknown", "Unbekannt", False)])
    before = (src / "de.po").read_text(encoding="utf-8")
    assert _run(src, pot, export, "--apply") != 0
    assert (src / "de.po").read_text(encoding="utf-8") == before


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    """Without --apply the catalog is unchanged."""
    src, pot, export = _fixture(tmp_path, [("Delete", "Löschen", False)])
    before = (src / "de.po").read_text(encoding="utf-8")
    assert _run(src, pot, export) == 0
    assert (src / "de.po").read_text(encoding="utf-8") == before


def test_language_pack_tree_imports_only_the_domain(tmp_path: Path) -> None:
    """A language-pack tree contributes only scantpaper's catalog."""
    src = tmp_path / "po" / "scantpaper"
    pot = src / "scantpaper.pot"
    _write(pot, [("Delete", "", False)])
    _write(src / "de.po", [("Delete", "Alt", True)])
    tree = tmp_path / "usr" / "share" / "locale"
    _write(
        tree / "de" / "LC_MESSAGES" / "scantpaper.po",
        [("Delete", "Löschen", False)],
    )
    _write(
        tree / "de" / "LC_MESSAGES" / "other.po",
        [("Delete", "Andere", False)],
    )

    assert _run(src, pot, tree, "--apply") == 0
    assert polib.pofile(str(src / "de.po")).find("Delete").msgstr == "Löschen"
