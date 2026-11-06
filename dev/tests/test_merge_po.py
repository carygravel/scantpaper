"""Tests for the deterministic catalog merge in dev/merge_po.py."""

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
MERGE_PATH = DEV_DIR / "merge_po.py"

sys.path.insert(0, str(DEV_DIR))
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load_merge() -> ModuleType:
    """Import dev/merge_po.py with its sibling and package paths."""
    spec = importlib.util.spec_from_file_location("merge_po", str(MERGE_PATH))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["merge_po"] = module
    spec.loader.exec_module(module)
    return module


MERGE = _load_merge()


def _write_pot(path: Path, msgids: list[str]) -> None:
    """Write a message template with the given msgids."""
    po = polib.POFile()
    po.metadata = {
        "Project-Id-Version": "test",
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
        "POT-Creation-Date": "2026-01-01 00:00+0000",
    }
    for index, msgid in enumerate(msgids):
        po.append(
            polib.POEntry(
                msgid=msgid,
                msgstr="",
                occurrences=[("app.py", str(10 + index))],
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(path))


def _write_catalog(path: Path, entries: list[tuple[str, str, bool]]) -> None:
    """Write a catalog with (msgid, msgstr, fuzzy) triples."""
    po = polib.POFile()
    po.metadata = {
        "Project-Id-Version": "test",
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
        "POT-Creation-Date": "2026-01-01 00:00+0000",
        "PO-Revision-Date": "2026-01-01 00:00+0000",
    }
    for index, (msgid, msgstr, fuzzy) in enumerate(entries):
        entry = polib.POEntry(
            msgid=msgid,
            msgstr=msgstr,
            occurrences=[("app.py", str(10 + index))],
        )
        if fuzzy:
            entry.flags.append("fuzzy")
        po.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(path))


def test_second_merge_on_unchanged_inputs_produces_no_diff(tmp_path: Path) -> None:
    """The merge is idempotent, including header dates."""
    pot = tmp_path / "scantpaper.pot"
    catalog = tmp_path / "de.po"
    _write_pot(pot, ["Keep", "Fuzzy"])
    _write_catalog(catalog, [("Keep", "Behalten", False), ("Fuzzy", "Unscharf", True)])

    MERGE.merge_catalogs(tmp_path, pot)
    first = catalog.read_bytes()
    MERGE.merge_catalogs(tmp_path, pot)
    assert catalog.read_bytes() == first


def test_changed_msgid_records_its_predecessor(tmp_path: Path) -> None:
    """A changed source string keeps the previous msgid and fuzzy text."""
    pot = tmp_path / "scantpaper.pot"
    catalog = tmp_path / "de.po"
    _write_pot(pot, ["Old label"])
    _write_catalog(catalog, [("Old label", "Alte Bezeichnung", False)])
    MERGE.merge_catalogs(tmp_path, pot)

    _write_pot(pot, ["New label"])
    MERGE.merge_catalogs(tmp_path, pot)

    po = polib.pofile(str(catalog))
    entry = po.find("New label")
    assert entry is not None
    assert entry.previous_msgid == "Old label"
    assert entry.msgstr == ""
    assert "fuzzy" not in entry.flags


def test_existing_fuzzy_flags_are_preserved(tmp_path: Path) -> None:
    """A merge does not clear a fuzzy proposal or fuzz a reviewed entry."""
    pot = tmp_path / "scantpaper.pot"
    catalog = tmp_path / "de.po"
    _write_pot(pot, ["Fuzzy", "Reviewed"])
    _write_catalog(
        catalog,
        [("Fuzzy", "Unscharf", True), ("Reviewed", "Geprüft", False)],
    )

    MERGE.merge_catalogs(tmp_path, pot)

    po = polib.pofile(str(catalog))
    assert "fuzzy" in po.find("Fuzzy").flags
    assert "fuzzy" not in po.find("Reviewed").flags


def test_similar_msgid_does_not_adopt_a_fuzzy_match(tmp_path: Path) -> None:
    """--no-fuzzy-matching leaves a new msgid untranslated."""
    pot = tmp_path / "scantpaper.pot"
    catalog = tmp_path / "de.po"
    _write_pot(pot, ["Open file"])
    _write_catalog(catalog, [("Open file", "Datei öffnen", False)])
    MERGE.merge_catalogs(tmp_path, pot)

    _write_pot(pot, ["Open file", "Open file now"])
    MERGE.merge_catalogs(tmp_path, pot)

    entry = polib.pofile(str(catalog)).find("Open file now")
    assert entry is not None
    assert entry.msgstr == ""
    assert "fuzzy" not in entry.flags


def test_unchanged_template_is_not_rewritten(tmp_path: Path) -> None:
    """An unchanged message set keeps the template's original date."""
    pot = tmp_path / "scantpaper.pot"
    _write_pot(pot, ["Keep"])
    original = pot.read_bytes()
    generated = (
        'msgid ""\nmsgstr ""\n'
        '"Content-Type: text/plain; charset=UTF-8\\n"\n'
        '"POT-Creation-Date: 2026-09-09 00:00+0000\\n"\n\n'
        'msgid "Keep"\nmsgstr ""\n'
    )

    assert not MERGE.write_template(pot, generated)
    assert pot.read_bytes() == original
