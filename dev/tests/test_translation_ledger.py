"""Tests for the translation approval ledger in dev/translation_ledger.py."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

import polib
import pytest

if TYPE_CHECKING:
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "dev"
LEDGER_MODULE_PATH = DEV_DIR / "translation_ledger.py"
LEDGER_PATH = REPO_ROOT / "po" / "translation-approvals.json"
FINDINGS_PATH = REPO_ROOT / "po" / "README.md"

sys.path.insert(0, str(DEV_DIR))


def _load_ledger_module() -> ModuleType:
    """Import dev/translation_ledger.py with its sibling policy module."""
    spec = importlib.util.spec_from_file_location(
        "translation_ledger", str(LEDGER_MODULE_PATH)
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["translation_ledger"] = module
    spec.loader.exec_module(module)
    return module


LEDGER = _load_ledger_module()


def _record(**overrides: object) -> dict[str, object]:
    """Build a valid human historical record."""
    msgstr = cast("str", overrides.pop("msgstr", "Löschen"))
    record: dict[str, object] = {
        "language": "de",
        "msgctxt": None,
        "msgid": "Delete",
        "msgid_plural": None,
        "msgstr": msgstr,
        "translation_sha256": LEDGER.translation_digest(msgstr),
        "provenance_class": "human-historical",
        "evidence": {},
        "model_release": None,
        "deployment": None,
        "approval_date": "2026-02-28",
    }
    record.update(overrides)
    return record


def _ledger(*records: dict[str, object]) -> dict[str, object]:
    """Wrap records in a valid ledger document."""
    return {"version": 1, "snapshot": "a" * 40, "approvals": list(records)}


def _entry(msgid: str = "Delete", msgstr: str = "Löschen") -> polib.POEntry:
    """Build a non-obsolete catalog entry."""
    return polib.POEntry(msgid=msgid, msgstr=msgstr)


def test_committed_ledger_is_valid() -> None:
    """The committed ledger has the documented version and snapshot."""
    data = LEDGER.load_ledger(LEDGER_PATH)
    assert data["version"] == 1
    assert data["snapshot"] == "1a3037183eadc10004f7f4d6228bd7f9192aa2ec"
    assert len(LEDGER.approvals(data)) > 0


def test_unknown_provenance_class_is_rejected() -> None:
    """A class outside the six defined classes cannot be approved."""
    with pytest.raises(LEDGER.LedgerError, match="unknown provenance class"):
        LEDGER.validate_ledger(_ledger(_record(provenance_class="machine-perfect")))


def test_missing_digest_is_rejected() -> None:
    """A record without translation_sha256 cannot approve an entry."""
    record = _record()
    del record["translation_sha256"]
    with pytest.raises(LEDGER.LedgerError, match="no translation_sha256"):
        LEDGER.validate_ledger(_ledger(record))


def test_malformed_digest_is_rejected() -> None:
    """A digest that is not 64 lower-case hex characters is rejected."""
    with pytest.raises(LEDGER.LedgerError, match="malformed translation_sha256"):
        LEDGER.validate_ledger(_ledger(_record(translation_sha256="abc")))


def test_digest_must_match_the_stored_translation() -> None:
    """A hand-edited translation invalidates its own record."""
    record = _record()
    record["msgstr"] = "Entfernen"
    with pytest.raises(LEDGER.LedgerError, match="does not match"):
        LEDGER.validate_ledger(_ledger(record))


def test_duplicate_approval_key_is_rejected() -> None:
    """Two records cannot approve the same content key twice."""
    with pytest.raises(LEDGER.LedgerError, match="duplicate approval"):
        LEDGER.validate_ledger(_ledger(_record(), _record()))


def test_machine_record_needs_release_and_deployment() -> None:
    """A machine approval records the release and deployment that produced it."""
    record = _record(provenance_class="machine-strong")
    with pytest.raises(LEDGER.LedgerError, match="no model_release"):
        LEDGER.validate_ledger(_ledger(record))


def test_plural_digest_is_order_independent() -> None:
    """Plural forms hash the same regardless of insertion order."""
    forms = {"1": "zwei", "0": "eins"}
    reversed_forms = {"0": "eins", "1": "zwei"}
    assert LEDGER.translation_digest("", forms) == LEDGER.translation_digest(
        "", reversed_forms
    )


def test_valid_approval_binds_to_the_catalog_entry() -> None:
    """A matching language, context, msgid and digest approves the entry."""
    data = LEDGER.validate_ledger(_ledger(_record()))
    entry = _entry()
    assert LEDGER.approval_for_entry(data, "de", entry) is not None
    assert LEDGER.validate_against_catalog(data, "de", _po(entry)) == []


def test_mutated_translation_invalidates_the_approval() -> None:
    """Editing msgstr makes the approval unusable and is reported."""
    data = LEDGER.validate_ledger(_ledger(_record()))
    entry = _entry()
    entry.msgstr = "Entfernen"
    assert LEDGER.approval_for_entry(data, "de", entry) is None
    problems = LEDGER.validate_against_catalog(data, "de", _po(entry))
    assert problems == ["de: approval for 'Delete' has a stale translation digest"]


def test_changed_msgid_is_reported_as_unbound() -> None:
    """A source-string change leaves the old approval with no entry."""
    data = LEDGER.validate_ledger(_ledger(_record()))
    entry = _entry(msgid="Remove")
    assert LEDGER.approval_for_entry(data, "de", entry) is None
    problems = LEDGER.validate_against_catalog(data, "de", _po(entry))
    assert problems == ["de: approval for 'Delete' does not match an active entry"]


def test_context_mismatch_is_reported_as_unbound() -> None:
    """Approvals are scoped to a message context."""
    data = LEDGER.validate_ledger(_ledger(_record()))
    entry = _entry()
    entry.msgctxt = "button"
    problems = LEDGER.validate_against_catalog(data, "de", _po(entry))
    assert problems == ["de: approval for 'Delete' does not match an active entry"]


def test_other_languages_are_not_reported() -> None:
    """The ledger covers every catalog, so another language is not an orphan."""
    data = LEDGER.validate_ledger(_ledger(_record(language="fr")))
    problems = LEDGER.validate_against_catalog(data, "de", _po(_entry()))
    assert problems == []


def test_ledger_written_by_json_round_trips(tmp_path: Path) -> None:
    """A ledger written to disk loads with the same approvals."""
    path = tmp_path / "translation-approvals.json"
    path.write_text(json.dumps(_ledger(_record())), encoding="utf-8")
    data = LEDGER.load_ledger(path)
    assert len(data["approvals"]) == 1


def test_documented_example_round_trips_through_the_helpers() -> None:
    """The example in po/README.md is a loadable approval."""
    text = FINDINGS_PATH.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)```", text, re.DOTALL)
    example = next(block for block in blocks if "translation_sha256" in block)

    data = LEDGER.validate_ledger(json.loads(example))
    record = cast("dict[str, object]", data["approvals"][0])
    entry = _entry(
        msgid=cast("str", record["msgid"]),
        msgstr=cast("str", record["msgstr"]),
    )
    assert LEDGER.approval_for_entry(data, "de", entry) is not None


def _po(*entries: polib.POEntry) -> polib.POFile:
    """Build a POFile from entries."""
    po = polib.POFile()
    for entry in entries:
        po.append(entry)
    return po
