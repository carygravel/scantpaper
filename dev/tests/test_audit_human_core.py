"""Tests for the human-core audit in dev/audit_human_core.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

import polib

if TYPE_CHECKING:
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "dev"
AUDIT_PATH = DEV_DIR / "audit_human_core.py"

sys.path.insert(0, str(DEV_DIR))


def _load_audit() -> ModuleType:
    """Import dev/audit_human_core.py with its sibling modules."""
    spec = importlib.util.spec_from_file_location("audit_human_core", str(AUDIT_PATH))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["audit_human_core"] = module
    spec.loader.exec_module(module)
    return module


AUDIT = _load_audit()
LEDGER = sys.modules["translation_ledger"]


def _git(repo: Path, *args: str) -> str:
    """Run git in the temporary repository."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _write_po(path: Path, entries: list[tuple[str, str]]) -> None:
    """Write a minimal catalog with the given (msgid, msgstr) pairs."""
    po = polib.POFile()
    po.metadata = {
        "Project-Id-Version": "test",
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
    }
    for msgid, msgstr in entries:
        po.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    path.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(path))


def _repository(
    tmp_path: Path,
    snapshot: list[tuple[str, str]],
    current: list[tuple[str, str]],
) -> str:
    """Create a repository with a snapshot commit and a current commit."""
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    _write_po(tmp_path / "po" / "scantpaper-de.po", snapshot)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "snapshot")
    snapshot_id = _git(tmp_path, "rev-parse", "HEAD").strip()

    _write_po(tmp_path / "po" / "scantpaper" / "de.po", current)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "current")
    return snapshot_id


def _multilingual_repository(
    tmp_path: Path,
    snapshot: dict[str, list[tuple[str, str]]],
    current: dict[str, list[tuple[str, str]]],
) -> str:
    """Create a repository whose snapshot and current tree hold many catalogs."""
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    for language, entries in snapshot.items():
        _write_po(tmp_path / "po" / f"scantpaper-{language}.po", entries)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "snapshot")
    snapshot_id = _git(tmp_path, "rev-parse", "HEAD").strip()

    for language, entries in current.items():
        _write_po(tmp_path / "po" / "scantpaper" / f"{language}.po", entries)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "current")
    return snapshot_id


def test_audit_classifies_unchanged_changed_and_added(tmp_path: Path) -> None:
    """Every shipped entry lands in exactly one of the three classes."""
    snapshot_id = _repository(
        tmp_path,
        [("Keep", "Behalten"), ("Old", "Alt"), ("Empty", "")],
        [("Keep", "Behalten"), ("Old", "Neu"), ("Empty", "Gefüllt"), ("New", "Neu")],
    )
    result = AUDIT.audit_catalogs(tmp_path, snapshot=snapshot_id)
    by_msgid = {entry.entry.msgid: entry for entry in result.entries}

    assert by_msgid["Keep"].category == AUDIT.UNCHANGED
    assert by_msgid["Old"].category == AUDIT.MODEL_CHANGED
    assert by_msgid["Empty"].category == AUDIT.MODEL_CHANGED
    assert by_msgid["New"].category == AUDIT.MODEL_ADDED

    totals = AUDIT._totals(result)
    assert totals == {
        "shipped": 4,
        AUDIT.UNCHANGED: 1,
        AUDIT.MODEL_CHANGED: 2,
        AUDIT.MODEL_ADDED: 1,
        "approved": 2,
        "pending": 2,
        "restored": 1,
    }


def test_unchanged_entry_becomes_human_historical(tmp_path: Path) -> None:
    """Unchanged pre-2026 text is approved without a new reviewer."""
    snapshot_id = _repository(
        tmp_path, [("Delete", "Löschen")], [("Delete", "Löschen")]
    )
    result = AUDIT.audit_catalogs(tmp_path, snapshot=snapshot_id)
    assert len(result.records) == 1
    assert result.records[0]["provenance_class"] == "human-historical"


def test_placeholder_rebase_is_approved_in_project(tmp_path: Path) -> None:
    """A placeholder-only fix of human text is an in-project rebase."""
    snapshot_id = _repository(
        tmp_path,
        [("Error: %s", "Errore: % s")],
        [("Error: %s", "Errore: %s")],
    )
    result = AUDIT.audit_catalogs(tmp_path, snapshot=snapshot_id)
    assert result.records[0]["provenance_class"] == "in-project-rebase"
    assert result.restored == []


def test_defect_fix_waits_for_the_gate(tmp_path: Path) -> None:
    """A defect repair is kept but not approved without the gate."""
    snapshot_id = _repository(
        tmp_path,
        [("Error: %s", "Errore: %d")],
        [("Error: %s", "Errore: %s")],
    )
    result = AUDIT.audit_catalogs(tmp_path, snapshot=snapshot_id)
    assert result.entries[0].decision.action == AUDIT.PENDING
    assert result.entries[0].decision.reason == "gate-required"
    assert result.records == []


def test_gate_approval_keeps_a_defect_fix_as_machine_strong(tmp_path: Path) -> None:
    """The gate can promote a defect repair to a machine-strong approval."""
    snapshot_id = _repository(
        tmp_path,
        [("Error: %s", "Errore: %d")],
        [("Error: %s", "Errore: %s")],
    )
    verdict = AUDIT.MachineVerdict(
        model_release="family/model@1",
        deployment="provider-a",
        evidence={"judge": "agrees"},
    )
    result = AUDIT.audit_catalogs(tmp_path, snapshot=snapshot_id, machine=verdict)
    assert result.records[0]["provenance_class"] == "machine-strong"
    assert result.records[0]["model_release"] == "family/model@1"
    assert result.records[0]["deployment"] == "provider-a"


def test_rewrite_restores_human_text_and_parks_the_variant(tmp_path: Path) -> None:
    """A non-mechanical model rewrite is reverted and kept for review."""
    snapshot_id = _repository(tmp_path, [("Open", "Öffnen")], [("Open", "Aufmachen")])
    result = AUDIT.audit_catalogs(tmp_path, snapshot=snapshot_id)

    assert result.entries[0].entry.msgstr == "Öffnen"
    record = result.records[0]
    assert record["provenance_class"] == "human-historical"
    evidence = record["evidence"]
    assert isinstance(evidence, dict)
    assert evidence["parked_fuzzy"] is True
    assert evidence["model_variant"] == {"msgstr": "Aufmachen", "msgstr_plural": {}}


def test_report_accounts_for_every_shipped_entry(tmp_path: Path) -> None:
    """Approved plus pending entries equal the shipped total."""
    snapshot_id = _repository(
        tmp_path,
        [("Keep", "Behalten"), ("Old", "Alt")],
        [("Keep", "Behalten"), ("Old", "Neu"), ("New", "Neu")],
    )
    result = AUDIT.audit_catalogs(tmp_path, snapshot=snapshot_id)
    report = AUDIT.build_report(result)
    totals = cast("dict[str, int]", report["totals"])
    assert totals["approved"] + totals["pending"] == totals["shipped"]
    assert totals["shipped"] == len(result.entries)


def test_apply_writes_a_valid_ledger_and_report(tmp_path: Path) -> None:
    """The CLI writes a loadable ledger and a deterministic report."""
    snapshot_id = _repository(
        tmp_path,
        [("Delete", "Löschen")],
        [("Delete", "Löschen")],
    )
    ledger = tmp_path / "translation-approvals.json"
    report = tmp_path / "translation-audit.json"
    status = AUDIT.main(
        [
            "--repo",
            str(tmp_path),
            "--snapshot",
            snapshot_id,
            "--ledger",
            str(ledger),
            "--report",
            str(report),
            "--apply",
        ]
    )
    assert status == 0

    data = json.loads(ledger.read_text(encoding="utf-8"))
    loaded = AUDIT.load_ledger(ledger)
    assert loaded["snapshot"] == snapshot_id
    assert len(data["approvals"]) == 1
    assert json.loads(report.read_text(encoding="utf-8"))["totals"]["shipped"] == 1


def test_scoped_report_merge_keeps_other_languages(tmp_path: Path) -> None:
    """A scoped audit replaces one block and leaves the rest intact."""
    snapshot_id = _multilingual_repository(
        tmp_path,
        {"de": [("Keep", "Behalten")], "fr": [("Garde", "Garder"), ("Old", "Vieux")]},
        {
            "de": [("Keep", "Behalten")],
            "fr": [("Garde", "Garder"), ("Old", "Nouveau"), ("New", "Neuf")],
        },
    )
    full = AUDIT.build_report(AUDIT.audit_catalogs(tmp_path, snapshot=snapshot_id))
    full_totals = cast("dict[str, int]", full["totals"])
    assert (
        f"grand total is {full_totals['shipped']}."
        in cast("list[str]", full["notes"])[0]
    )

    _write_po(
        tmp_path / "po" / "scantpaper" / "de.po",
        [("Keep", "Behalten"), ("Brand", "Neu")],
    )
    scoped = AUDIT.audit_catalogs(tmp_path, snapshot=snapshot_id, languages=["de"])
    merged = AUDIT.merge_report(full, scoped)

    assert merged["languages"]["fr"] == full["languages"]["fr"]
    assert merged["languages"]["de"]["shipped"] == 2
    totals = cast("dict[str, int]", merged["totals"])
    assert totals["shipped"] == 5
    assert totals["approved"] + totals["pending"] == totals["shipped"]
    assert (
        f"grand total is {totals['shipped']}." in cast("list[str]", merged["notes"])[0]
    )

    fr_pending = [item for item in full["pending"] if item["language"] == "fr"]
    merged_fr = [item for item in merged["pending"] if item["language"] == "fr"]
    assert merged_fr == fr_pending
    de_pending = [item for item in merged["pending"] if item["language"] == "de"]
    assert [item["msgid"] for item in de_pending] == ["Brand"]


def test_scoped_report_merge_rebuilds_on_a_new_snapshot(tmp_path: Path) -> None:
    """Blocks from two snapshots are never merged."""
    snapshot_id = _repository(tmp_path, [("Keep", "Behalten")], [("Keep", "Behalten")])
    result = AUDIT.audit_catalogs(tmp_path, snapshot=snapshot_id)
    existing = {
        "version": 1,
        "snapshot": "b" * 40,
        "snapshot_date": "2020-01-01",
        "totals": {"shipped": 1},
        "languages": {"fr": {"shipped": 1}},
        "pending": [],
        "parked": [],
        "notes": [],
    }
    merged = AUDIT.merge_report(existing, result)
    assert merged == AUDIT.build_report(result)
    assert "fr" not in merged["languages"]


def test_scoped_apply_leaves_other_ledgers_untouched(tmp_path: Path) -> None:
    """Only the audited language's ledger file is rewritten."""
    snapshot_id = _multilingual_repository(
        tmp_path,
        {"de": [("Delete", "Löschen")], "fr": [("Delete", "Supprimer")]},
        {"de": [("Delete", "Löschen")], "fr": [("Delete", "Supprimer")]},
    )
    ledger = tmp_path / "approvals"
    report = tmp_path / "translation-audit.json"
    base = [
        "--repo",
        str(tmp_path),
        "--snapshot",
        snapshot_id,
        "--ledger",
        str(ledger),
        "--report",
        str(report),
        "--apply",
    ]
    assert AUDIT.main([*base, "--language", "fr"]) == 0
    fr_before = (ledger / "fr.json").read_bytes()
    first_report = json.loads(report.read_text(encoding="utf-8"))

    assert AUDIT.main([*base, "--language", "de"]) == 0

    assert (ledger / "fr.json").read_bytes() == fr_before
    de_data = json.loads((ledger / "de.json").read_text(encoding="utf-8"))
    assert len(de_data["approvals"]) == 1
    merged_report = json.loads(report.read_text(encoding="utf-8"))
    assert set(merged_report["languages"]) == {"de", "fr"}
    assert merged_report["languages"]["fr"] == first_report["languages"]["fr"]


def test_committed_report_accounts_for_every_shipped_entry() -> None:
    """Every shipped entry has an approval or is named as pending."""
    ledger = AUDIT.load_ledger(REPO_ROOT / "po" / "approvals")
    report = json.loads(
        (REPO_ROOT / "po" / "translation-audit.json").read_text(encoding="utf-8")
    )
    pending = {
        (item["language"], item["msgctxt"], item["msgid"], item["msgid_plural"])
        for item in report["pending"]
    }
    index = LEDGER.approval_index(ledger)

    shipped = 0
    for path in sorted((REPO_ROOT / "po" / "scantpaper").glob("*.po")):
        po = polib.pofile(str(path))
        for entry in po:
            if entry.obsolete or not entry.msgid or "fuzzy" in entry.flags:
                continue
            if not AUDIT.has_text(entry):
                continue
            shipped += 1
            record = index.get(LEDGER.entry_key(path.stem, entry))
            if record is None or record.get(
                "translation_sha256"
            ) != LEDGER.entry_digest(entry):
                key = (
                    path.stem,
                    entry.msgctxt or None,
                    entry.msgid,
                    entry.msgid_plural or None,
                )
                assert key in pending

    totals = report["totals"]
    assert totals["shipped"] == shipped
    assert totals["unchanged"] == 9691
    assert totals["model-changed"] == 1734
    assert totals["approved"] + totals["pending"] == shipped
    assert shipped == 17641
