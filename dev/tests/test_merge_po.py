"""Tests for the deterministic catalog merge in dev/merge_po.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock

import polib
import pytest

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


def test_changed_msgid_predecessor_survives_a_second_merge(
    tmp_path: Path,
) -> None:
    """A repeated merge keeps the recorded predecessor and changes nothing."""
    pot = tmp_path / "scantpaper.pot"
    catalog = tmp_path / "de.po"
    _write_pot(pot, ["Old label"])
    _write_catalog(catalog, [("Old label", "Alte Bezeichnung", False)])
    MERGE.merge_catalogs(tmp_path, pot)

    _write_pot(pot, ["New label"])
    MERGE.merge_catalogs(tmp_path, pot, languages=["de"])
    first = catalog.read_bytes()

    changed = MERGE.merge_catalogs(tmp_path, pot, languages=["de"])

    assert changed == []
    assert catalog.read_bytes() == first
    entry = polib.pofile(str(catalog)).find("New label")
    assert entry is not None
    assert entry.previous_msgid == "Old label"


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


def test_select_catalogs_returns_only_named_languages(tmp_path: Path) -> None:
    """A named selection returns the matching catalogs in sorted order."""
    for language in ("de", "es", "fr"):
        _write_catalog(tmp_path / f"{language}.po", [("Keep", language, False)])

    selected = MERGE.select_catalogs(tmp_path, ["es", "de"])

    assert [path.stem for path in selected] == ["de", "es"]


def test_select_catalogs_deduplicates_names(tmp_path: Path) -> None:
    """Repeating a language selects its catalog once."""
    _write_catalog(tmp_path / "de.po", [("Keep", "Behalten", False)])

    selected = MERGE.select_catalogs(tmp_path, ["de", "de"])

    assert [path.stem for path in selected] == ["de"]


def test_select_catalogs_rejects_an_unknown_language(tmp_path: Path) -> None:
    """An unknown name fails and names the available languages."""
    for language in ("de", "es"):
        _write_catalog(tmp_path / f"{language}.po", [("Keep", language, False)])

    with pytest.raises(
        MERGE.MergeError,
        match=r"unknown language\(s\): dee \(available: de, es\)",
    ):
        MERGE.select_catalogs(tmp_path, ["dee"])


def test_unknown_language_fails_before_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A typo leaves the template and every catalog untouched."""
    src = tmp_path / "po"
    _write_catalog(src / "de.po", [("Keep", "Behalten", False)])
    catalog_bytes = (src / "de.po").read_bytes()
    pot = tmp_path / "scantpaper.pot"
    _write_pot(pot, ["Keep"])
    pot_bytes = pot.read_bytes()
    monkeypatch.setattr(MERGE, "DEFAULT_POT", pot)
    generator = Mock(side_effect=AssertionError("generated before validation"))
    monkeypatch.setattr(MERGE, "generate_template", generator)

    result = MERGE.main(["--src", str(src), "--language", "dee"])

    assert result == 1
    assert "unknown language(s): dee" in capsys.readouterr().err
    generator.assert_not_called()
    assert pot.read_bytes() == pot_bytes
    assert (src / "de.po").read_bytes() == catalog_bytes


def test_help_lists_language_option(capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI advertises the repeatable option."""
    with pytest.raises(SystemExit) as exit_info:
        MERGE.main(["--help"])

    assert exit_info.value.code == 0
    assert "--language" in capsys.readouterr().out


def test_merge_catalogs_without_languages_merges_every_catalog(
    tmp_path: Path,
) -> None:
    """The default selection still refreshes every catalog."""
    pot = tmp_path / "scantpaper.pot"
    _write_pot(pot, ["Keep"])
    for language in ("de", "es"):
        _write_catalog(tmp_path / f"{language}.po", [("Old", "Alt", False)])

    changed = MERGE.merge_catalogs(tmp_path, pot)

    assert changed == ["de", "es"]
    for language in ("de", "es"):
        catalog = polib.pofile(str(tmp_path / f"{language}.po"))
        assert catalog.find("Keep") is not None


def test_named_selection_leaves_other_catalogs_untouched(
    tmp_path: Path,
) -> None:
    """Only the selected catalog changes."""
    pot = tmp_path / "scantpaper.pot"
    _write_pot(pot, ["Keep"])
    for language in ("de", "es"):
        _write_catalog(tmp_path / f"{language}.po", [("Old", "Alt", False)])
    es_bytes = (tmp_path / "es.po").read_bytes()

    changed = MERGE.merge_catalogs(tmp_path, pot, languages=["de"])

    assert changed == ["de"]
    assert (tmp_path / "es.po").read_bytes() == es_bytes
    assert polib.pofile(str(tmp_path / "de.po")).find("Keep") is not None


def test_main_merges_only_the_named_catalog(tmp_path: Path) -> None:
    """The CLI routes its selection through the same guard."""
    src = tmp_path / "po"
    pot = tmp_path / "scantpaper.pot"
    _write_pot(pot, ["Keep"])
    for language in ("de", "es"):
        _write_catalog(src / f"{language}.po", [("Old", "Alt", False)])
    es_bytes = (src / "es.po").read_bytes()

    result = MERGE.main(["--src", str(src), "--pot", str(pot), "--language", "de"])

    assert result == 0
    assert (src / "es.po").read_bytes() == es_bytes
    assert polib.pofile(str(src / "de.po")).find("Keep") is not None


def test_summary_reports_selected_and_changed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A filtered run reports both counts and names the changed catalog."""
    src = tmp_path / "po"
    pot = tmp_path / "scantpaper.pot"
    _write_pot(pot, ["Keep"])
    _write_catalog(src / "de.po", [("Old", "Alt", False)])
    _write_catalog(src / "es.po", [("Keep", "Mantener", False)])

    result = MERGE.main(
        [
            "--src",
            str(src),
            "--pot",
            str(pot),
            "--language",
            "de",
            "--language",
            "es",
        ]
    )

    assert result == 0
    assert "1 of 2 selected catalog(s) changed: de" in capsys.readouterr().out


def test_scoped_merge_matches_the_full_merge(tmp_path: Path) -> None:
    """A selected catalog is byte-identical whether merged alone or with all."""
    pot = tmp_path / "scantpaper.pot"
    _write_pot(pot, ["Keep"])
    scoped = tmp_path / "scoped"
    full = tmp_path / "full"
    for root in (scoped, full):
        for language in ("de", "es"):
            _write_catalog(root / f"{language}.po", [("Old", "Alt", False)])

    MERGE.merge_catalogs(scoped, pot, languages=["de"])
    MERGE.merge_catalogs(full, pot)

    assert (scoped / "de.po").read_bytes() == (full / "de.po").read_bytes()
    assert (scoped / "es.po").read_bytes() != (full / "es.po").read_bytes()


def test_filtered_second_run_changes_nothing(tmp_path: Path) -> None:
    """A second scoped merge on unchanged inputs is a no-op."""
    pot = tmp_path / "scantpaper.pot"
    _write_pot(pot, ["Keep"])
    _write_catalog(tmp_path / "de.po", [("Old", "Alt", False)])

    MERGE.merge_catalogs(tmp_path, pot, languages=["de"])
    first = (tmp_path / "de.po").read_bytes()

    changed = MERGE.merge_catalogs(tmp_path, pot, languages=["de"])

    assert changed == []
    assert (tmp_path / "de.po").read_bytes() == first
