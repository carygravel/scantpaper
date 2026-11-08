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
LEDGER_PATH = REPO_ROOT / "po" / "approvals"
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


def test_plural_record_stores_string_keys() -> None:
    """make_record stores plural keys as strings that validate and apply."""
    entry = polib.POEntry(
        msgid="File",
        msgid_plural="Files",
        msgstr_plural={0: "Datei", 1: "Dateien"},
    )
    record = cast(
        "dict[str, object]",
        LEDGER.make_record(
            "de",
            entry,
            "human-review",
            context=LEDGER.ApprovalContext(approval_date="2026-01-01"),
        ),
    )
    assert record["msgstr_plural"] == {"0": "Datei", "1": "Dateien"}
    LEDGER.validate_record(record, index=0)
    assert LEDGER.approval_for_entry(_ledger(record), "de", entry) == record

    changed = dict(record)
    changed["translation_sha256"] = "0" * 64
    with pytest.raises(LEDGER.LedgerError, match="does not match"):
        LEDGER.validate_record(changed, index=0)


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


def test_split_ledger_round_trip(tmp_path: Path) -> None:
    """Per-language files merge back into the same approval set."""
    fr_entry = polib.POEntry(msgid="Open", msgstr="Ouvrir")
    fr_record = cast(
        "dict[str, object]",
        LEDGER.make_record(
            "fr",
            fr_entry,
            "human-historical",
            context=LEDGER.ApprovalContext(approval_date="2026-02-28"),
        ),
    )
    data: dict[str, object] = {
        "version": 1,
        "snapshot": "a" * 40,
        "approvals": [_record(), fr_record],
        "qualifications": [{"release": "r1", "language": "de"}],
        "conformances": [{"release": "r1", "deployment": "p1"}],
        "revocations": [{"scope": "language", "value": "fr"}],
        "gate_runs": [{"language": "de", "calls": []}],
    }
    LEDGER.write_ledger(data, tmp_path)
    assert (tmp_path / LEDGER.MANIFEST_NAME).exists()
    assert (tmp_path / LEDGER.GLOBAL_NAME).exists()
    assert (tmp_path / "de.json").exists()
    assert (tmp_path / "fr.json").exists()

    merged = LEDGER.load_ledger(tmp_path)
    assert len(LEDGER.approvals(merged)) == 2
    assert LEDGER.section(merged, "qualifications")
    assert LEDGER.section(merged, "conformances")
    assert LEDGER.section(merged, "revocations")

    de_data = LEDGER.load_language_ledger(tmp_path, "de")
    assert [record["language"] for record in LEDGER.approvals(de_data)] == ["de"]
    fr_before = (tmp_path / "fr.json").read_text(encoding="utf-8")
    approvals_list = cast("list[dict[str, object]]", de_data["approvals"])
    approvals_list.append(
        cast(
            "dict[str, object]",
            LEDGER.make_record(
                "de",
                polib.POEntry(msgid="Open", msgstr="Öffnen"),
                "human-historical",
                context=LEDGER.ApprovalContext(approval_date="2026-02-28"),
            ),
        )
    )
    LEDGER.write_language_ledger(de_data, tmp_path, "de")
    assert (tmp_path / "fr.json").read_text(encoding="utf-8") == fr_before


def test_split_ledger_rejects_duplicate_approvals(tmp_path: Path) -> None:
    """A duplicate approval key is rejected before it is written."""
    with pytest.raises(LEDGER.LedgerError, match="duplicate approval"):
        LEDGER.write_ledger(_ledger(_record(), _record()), tmp_path)


def test_evidence_store_dedupes_and_resolves(tmp_path: Path) -> None:
    """The sidecar stores one copy of a payload and resolves it by digest."""
    path = tmp_path / "evidence.ndjson"
    payload = {"calls": [{"cost_usd": 0.1}]}
    digest = LEDGER.write_evidence(payload, path, kind="gate_run", language="de")
    assert path.read_text(encoding="utf-8").count("\n") == 1
    assert (
        LEDGER.write_evidence(payload, path, kind="gate_run", language="de") == digest
    )
    assert path.read_text(encoding="utf-8").count("\n") == 1
    assert LEDGER.load_evidence(digest, path) == payload
    assert LEDGER.load_evidence("0" * 64, path) is None


def test_compact_approval_record_keeps_a_summary(tmp_path: Path) -> None:
    """Compaction moves the full evidence to the sidecar and keeps the digest."""
    evidence: dict[str, object] = {
        "proposals": [
            {
                "deployment": "p1",
                "release": "r1",
                "family": "family-a",
                "text": "Löschen",
                "call": {"cost_usd": 1.0},
            }
        ],
        "checks": {"p1": []},
        "judge": {"deployment": "j", "verdict": "A"},
        "calls": [{"cost_usd": 1.0}],
        "high_impact": False,
        "prompt_version": 1,
        "prompt_hash": "sha256:test",
    }
    record = cast(
        "dict[str, object]",
        LEDGER.make_record(
            "de",
            _entry(),
            "machine-strong",
            context=LEDGER.ApprovalContext(
                approval_date="2026-02-28",
                evidence=evidence,
                model_release="r1",
                deployment="p1",
            ),
        ),
    )
    path = tmp_path / "evidence.ndjson"
    LEDGER.compact_approval_record(record, path)
    summary = cast("dict[str, object]", record["evidence"])
    assert "calls" not in summary
    proposals = cast("list[dict[str, object]]", summary["proposals"])
    assert "text" not in proposals[0]
    digest = cast("str", record["evidence_sha256"])
    assert LEDGER.load_evidence(digest, path) == evidence
    LEDGER.validate_record(record, index=0)


def test_compact_operational_record_resolves_calls(tmp_path: Path) -> None:
    """A compact gate run can recover its calls from the sidecar."""
    path = tmp_path / "evidence.ndjson"
    record: dict[str, object] = {
        "language": "de",
        "calls": [{"cost_usd": 0.1}],
        "call_count": 1,
        "total_cost_usd": 0.1,
        "latency_ms": 1.0,
    }
    LEDGER.compact_operational_record(record, path, kind="gate_run")
    assert "calls" not in record
    assert LEDGER.load_gate_run_calls(record, path) == [{"cost_usd": 0.1}]
