"""Tests for the cross-project translation memory in dev/tm_index.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

import polib

if TYPE_CHECKING:
    from types import ModuleType

    import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "dev"
TM_PATH = DEV_DIR / "tm_index.py"

sys.path.insert(0, str(DEV_DIR))


def _load_tm() -> ModuleType:
    """Import dev/tm_index.py."""
    spec = importlib.util.spec_from_file_location("tm_index", str(TM_PATH))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["tm_index"] = module
    spec.loader.exec_module(module)
    return module


TM = _load_tm()


def _write_mo(path: Path, entries: list[tuple[str, str]]) -> None:
    """Write a compiled catalog with the given entries."""
    po = polib.POFile()
    po.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
    }
    for msgid, msgstr in entries:
        po.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    path.parent.mkdir(parents=True, exist_ok=True)
    po.save_as_mofile(str(path))


def _write_po(path: Path, entries: list[tuple[str, str]]) -> None:
    """Write an uncompiled catalog with the given entries."""
    po = polib.POFile()
    po.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
    }
    for msgid, msgstr in entries:
        po.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    path.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(path))


def _manifest(path: Path, rules: list[tuple[str, str]]) -> Path:
    """Write a manifest with project/licence rules for every language."""
    payload = {
        "version": 1,
        "sources": [
            {
                "project": project,
                "language": "*",
                "license": license_name,
                "origin": "test",
            }
            for project, license_name in rules
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _build(
    tmp_path: Path,
    rules: list[tuple[str, str]],
) -> tuple[Path, dict[str, object]]:
    """Build an index from a temporary installed-locale tree."""
    locale_root = tmp_path / "usr" / "share" / "locale"
    manifest = _manifest(tmp_path / "manifest.json", rules)
    db = tmp_path / "index.sqlite3"
    entries = TM.load_manifest(manifest)
    sources, skipped = TM.resolve_sources(entries, locale_root=locale_root)
    stats = TM.build_index(db, sources, skipped)
    return db, {
        "sources": stats.sources,
        "entries": stats.entries,
        "projects": stats.projects,
        "skipped": stats.skipped,
    }


def test_normalize_strips_mnemonics_and_case() -> None:
    """A mnemonic, case and whitespace difference is not a new source."""
    assert TM.normalize("_Save  &File") == TM.normalize("save file")


def test_licence_gate_excludes_gpl2_only(tmp_path: Path) -> None:
    """A GPL-2.0-only catalog is not evidence for a GPL-3.0-only project."""
    locale = tmp_path / "usr" / "share" / "locale"
    _write_mo(locale / "de" / "LC_MESSAGES" / "allowed.mo", [("Delete", "Löschen")])
    _write_mo(locale / "de" / "LC_MESSAGES" / "blocked.mo", [("Delete", "Entfernen")])
    db, stats = _build(
        tmp_path,
        [("allowed", "BSD-3-Clause"), ("blocked", "GPL-2.0-only")],
    )
    assert stats["sources"] == 1
    assert "blocked" not in cast("set[str]", stats["projects"])
    assert any(
        "GPL-2.0-only" in message for message in cast("list[str]", stats["skipped"])
    )
    assert TM.exact_matches(db, "Delete", "de") == [("Löschen", 1)]


def test_dominance_counts_projects_not_occurrences(tmp_path: Path) -> None:
    """One large catalog cannot outvote two projects that agree."""
    locale = tmp_path / "usr" / "share" / "locale"
    base = locale / "de" / "LC_MESSAGES"
    _write_mo(base / "first.mo", [("Delete", "Löschen")])
    _write_mo(base / "second.mo", [("Delete", "Löschen")])
    _write_mo(
        base / "large.mo",
        [("Delete", "Entfernen"), ("_Delete", "Entfernen"), ("Delete ", "Entfernen")],
    )
    db, _ = _build(
        tmp_path,
        [
            ("first", "BSD-3-Clause"),
            ("second", "GPL-3.0-or-later"),
            ("large", "BSD-3-Clause"),
        ],
    )
    assert TM.exact_matches(db, "Delete", "de") == [
        ("Löschen", 2),
        ("Entfernen", 1),
    ]
    assert TM.dominant_match(db, "Delete", "de") == "Löschen"


def test_tied_targets_are_not_dominant(tmp_path: Path) -> None:
    """Two equally supported targets leave the evidence ambiguous."""
    locale = tmp_path / "usr" / "share" / "locale"
    base = locale / "de" / "LC_MESSAGES"
    _write_mo(base / "first.mo", [("Delete", "Löschen")])
    _write_mo(base / "second.mo", [("Delete", "Löschen")])
    _write_mo(base / "third.mo", [("Delete", "Entfernen")])
    _write_mo(base / "fourth.mo", [("Delete", "Entfernen")])
    db, _ = _build(
        tmp_path,
        [
            ("first", "BSD-3-Clause"),
            ("second", "BSD-3-Clause"),
            ("third", "BSD-3-Clause"),
            ("fourth", "BSD-3-Clause"),
        ],
    )
    assert TM.dominant_match(db, "Delete", "de") is None


def test_rebuild_is_idempotent(tmp_path: Path) -> None:
    """Two builds over the same inputs produce the same counts."""
    locale = tmp_path / "usr" / "share" / "locale"
    _write_mo(locale / "de" / "LC_MESSAGES" / "one.mo", [("Delete", "Löschen")])
    first_db, _ = _build(tmp_path, [("one", "BSD-3-Clause")])
    first = TM.database_stats(first_db)
    second_db, _ = _build(tmp_path, [("one", "BSD-3-Clause")])
    second = TM.database_stats(second_db)
    assert first == second


def test_import_attributes_project_and_language(tmp_path: Path) -> None:
    """An imported upstream tree records its project and language."""
    tree = tmp_path / "upstream"
    _write_po(tree / "po" / "de.po", [("Delete", "Löschen")])
    manifest = _manifest(tmp_path / "manifest.json", [])
    db = tmp_path / "index.sqlite3"

    status = TM.main(
        [
            "--db",
            str(db),
            "--manifest",
            str(manifest),
            "--import",
            str(tree),
            "--project",
            "upstream",
            "--language",
            "de",
            "--license",
            "GPL-3.0-or-later",
        ]
    )
    assert status == 0
    stats = TM.database_stats(db)
    assert stats["sources"] == 1
    assert stats["by_project"] == [
        {"project": "upstream", "language": "de", "entries": 1}
    ]


def test_stats_command_names_project_and_language(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The stats report attributes entries to a project and language."""
    locale = tmp_path / "usr" / "share" / "locale"
    _write_mo(locale / "de" / "LC_MESSAGES" / "one.mo", [("Delete", "Löschen")])
    db, _ = _build(tmp_path, [("one", "BSD-3-Clause")])
    assert TM.main(["--db", str(db), "--stats"]) == 0
    captured = capsys.readouterr()
    assert "one" in captured.out
    assert "de" in captured.out
