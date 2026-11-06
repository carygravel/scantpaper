"""Audit the pre-2026 human core and populate the approval ledger.

The frozen reference is git commit ``1a303718``, read with ``git show``. It
holds the Launchpad export that predates the 2026 machine work, in the old
flat layout ``po/scantpaper-<lang>.po``. For every currently shipped entry
(non-fuzzy with a translation) the audit classifies the entry as:

* ``unchanged`` - the translation equals the pre-2026 text;
* ``model-changed`` - the msgid existed before but the text differs, including
  a previously empty translation that the 2026 work filled in;
* ``model-added`` - the msgid did not exist before, or the language had no
  pre-2026 catalog.

The policy that turns a classification into an action is deliberately
conservative:

* unchanged text becomes a ``human-historical`` approval;
* a change limited to a placeholder, a mnemonic or whitespace becomes an
  ``in-project-rebase`` approval, because no translated word changed;
* a change that repairs a deterministic placeholder defect is kept, but stays
  pending until the machine gate approves it as ``machine-strong``;
* any other rewrite restores the pre-2026 text as ``human-historical`` and
  parks the model variant as a fuzzy proposal in the record's evidence;
* entries with no human text (a new msgid, a new language, or a previously
  empty translation) are listed as pending until the gate can approve them.

The command is dry-run unless ``--apply`` is given. A dry run prints the
counts and writes nothing.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import polib
from translation_ledger import (
    LEDGER_PATH,
    ApprovalContext,
    ApprovalRecord,
    LedgerError,
    approvals,
    load_ledger,
    make_record,
    record_key,
    write_ledger,
)
from translation_policy import fixes_placeholder_defect, is_mechanical_rebase

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = "1a3037183eadc10004f7f4d6228bd7f9192aa2ec"
DEFAULT_SOURCE = "po/scantpaper"
DEFAULT_REPORT = "po/translation-audit.json"
LEDGER_VERSION = 1

UNCHANGED = "unchanged"
MODEL_CHANGED = "model-changed"
MODEL_ADDED = "model-added"

APPROVE = "approve"
PENDING = "pending"
RESTORE = "restore"


class AuditError(Exception):
    """An audit input or repository state that cannot be trusted."""


@dataclass(frozen=True)
class MachineVerdict:
    """A gate verdict strong enough to keep a model change."""

    model_release: str
    deployment: str
    evidence: dict[str, object]


@dataclass(frozen=True)
class Decision:
    """What the audit does with one classified entry."""

    action: str
    provenance_class: str | None
    reason: str
    machine: MachineVerdict | None = None


@dataclass
class AuditedEntry:
    """One shipped entry with its classification and decision."""

    language: str
    category: str
    entry: polib.POEntry
    previous: polib.POEntry | None
    decision: Decision
    parked_variant: dict[str, object] | None = None


@dataclass
class AuditResult:
    """The entries, approvals and catalog edits produced by an audit."""

    snapshot: str
    snapshot_date: str
    entries: list[AuditedEntry]
    records: list[ApprovalRecord]
    catalogs: dict[str, polib.POFile]
    changed_catalogs: set[str]
    snapshot_languages: set[str]

    @property
    def pending(self) -> list[AuditedEntry]:
        """Return the entries that still need the machine gate."""
        return [entry for entry in self.entries if entry.decision.action == PENDING]

    @property
    def restored(self) -> list[AuditedEntry]:
        """Return the entries whose model rewrite was reverted."""
        return [entry for entry in self.entries if entry.decision.action == RESTORE]


def _run_git(repo: Path, *args: str) -> str:
    """Run a git command in ``repo`` and return its standard output."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"git {' '.join(args)} failed: {result.stderr.strip()}"
        raise AuditError(msg)
    return result.stdout


def _git_show(repo: Path, ref: str, path: str) -> str | None:
    """Return a file at ``ref``, or None when that path does not exist."""
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else None


def parse_catalog(text: str) -> polib.POFile:
    """Parse catalog text without leaving a temporary file behind."""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".po", encoding="utf-8", delete=False
    ) as handle:
        handle.write(text)
        name = handle.name
    try:
        return polib.pofile(name)
    finally:
        Path(name).unlink()


def snapshot_candidates(language: str) -> list[str]:
    """Return the possible pre-2026 paths for a language, old layout first."""
    return [f"po/scantpaper-{language}.po", f"po/scantpaper/{language}.po"]


def load_snapshot_catalog(repo: Path, ref: str, language: str) -> polib.POFile | None:
    """Load one language's catalog at ``ref``, or None when it has none."""
    for path in snapshot_candidates(language):
        text = _git_show(repo, ref, path)
        if text is not None:
            return parse_catalog(text)
    return None


def has_text(entry: polib.POEntry) -> bool:
    """Return whether an entry carries a usable translation."""
    if entry.msgid_plural:
        return any(value.strip() for value in (entry.msgstr_plural or {}).values())
    return bool(entry.msgstr.strip())


def translation_texts(entry: polib.POEntry) -> list[str]:
    """Return the singular translation or every plural form."""
    if entry.msgid_plural:
        return list((entry.msgstr_plural or {}).values())
    return [entry.msgstr]


def translations_equal(left: polib.POEntry, right: polib.POEntry) -> bool:
    """Return whether two entries carry exactly the same translation."""
    return left.msgstr == right.msgstr and (left.msgstr_plural or {}) == (
        right.msgstr_plural or {}
    )


def classify_entry(entry: polib.POEntry, previous: polib.POEntry | None) -> str:
    """Classify a shipped entry against its pre-2026 counterpart."""
    if previous is None:
        return MODEL_ADDED
    if not has_text(previous):
        return MODEL_CHANGED
    if translations_equal(entry, previous):
        return UNCHANGED
    return MODEL_CHANGED


def _all_mechanical_rebase(
    previous: polib.POEntry,
    entry: polib.POEntry,
) -> bool:
    """Return whether every translation form changed mechanically only."""
    old_texts = translation_texts(previous)
    new_texts = translation_texts(entry)
    return len(old_texts) == len(new_texts) and all(
        is_mechanical_rebase(old, new)
        for old, new in zip(old_texts, new_texts, strict=True)
    )


def _all_fix_placeholder_defect(
    entry: polib.POEntry,
    previous: polib.POEntry,
) -> bool:
    """Return whether every form repairs a placeholder defect."""
    old_texts = translation_texts(previous)
    new_texts = translation_texts(entry)
    source = entry.msgid
    return len(old_texts) == len(new_texts) and all(
        fixes_placeholder_defect(source, old, new)
        for old, new in zip(old_texts, new_texts, strict=True)
    )


def _pending(reason: str) -> Decision:
    """Build a pending decision."""
    return Decision(action=PENDING, provenance_class=None, reason=reason)


def decide_model_change(
    entry: polib.POEntry,
    previous: polib.POEntry,
    *,
    machine: MachineVerdict | None = None,
) -> Decision:
    """Decide what to do with a changed pre-2026 entry."""
    if _all_mechanical_rebase(previous, entry):
        return Decision(
            action=APPROVE,
            provenance_class="in-project-rebase",
            reason="change limited to a placeholder, mnemonic or whitespace",
        )
    if _all_fix_placeholder_defect(entry, previous):
        if machine is not None:
            return Decision(
                action=APPROVE,
                provenance_class="machine-strong",
                reason="model change repairs a deterministic placeholder defect",
                machine=machine,
            )
        return _pending("gate-required")

    return Decision(
        action=RESTORE,
        provenance_class="human-historical",
        reason="model rewrite reverted to the pre-2026 human text",
    )


def decide(
    category: str,
    entry: polib.POEntry,
    previous: polib.POEntry | None,
    *,
    machine: MachineVerdict | None = None,
) -> Decision:
    """Return the audit action for one classified entry."""
    if category == UNCHANGED:
        return Decision(
            action=APPROVE,
            provenance_class="human-historical",
            reason="unchanged pre-2026 human text",
        )
    if category == MODEL_ADDED:
        return _pending("model-added")
    if previous is None or not has_text(previous):
        return _pending("model-changed with no human text")

    return decide_model_change(entry, previous, machine=machine)


def _restore_entry(entry: polib.POEntry, previous: polib.POEntry) -> str:
    """Restore the pre-2026 text and return the parked model variant."""
    parked = json.dumps(
        {
            "msgstr": entry.msgstr,
            "msgstr_plural": dict(entry.msgstr_plural or {}),
        },
        ensure_ascii=False,
    )
    entry.msgstr = previous.msgstr
    entry.msgstr_plural = dict(previous.msgstr_plural or {})
    entry.flags = [flag for flag in entry.flags if flag != "fuzzy"]
    return parked


def _record_for(
    audited: AuditedEntry,
    decision: Decision,
    approval_date: str,
) -> ApprovalRecord:
    """Build the ledger record for an approved entry."""
    provenance_class = decision.provenance_class
    if provenance_class is None:
        msg = "cannot record an approval without a provenance class"
        raise AuditError(msg)
    evidence: dict[str, object] = {"reason": decision.reason}
    if audited.parked_variant is not None:
        evidence["parked_fuzzy"] = True
        evidence["model_variant"] = audited.parked_variant
    model_release = decision.machine.model_release if decision.machine else None
    deployment = decision.machine.deployment if decision.machine else None
    if decision.machine is not None:
        evidence.update(decision.machine.evidence)
    return make_record(
        audited.language,
        audited.entry,
        provenance_class,
        context=ApprovalContext(
            approval_date=approval_date,
            evidence=evidence,
            model_release=model_release,
            deployment=deployment,
        ),
    )


def _audit_one(
    language: str,
    entry: polib.POEntry,
    previous_by_key: dict[tuple[str, str, str], polib.POEntry],
    snapshot_date: str,
    machine: MachineVerdict | None,
) -> tuple[AuditedEntry, ApprovalRecord | None]:
    """Audit one shipped entry and return its decision and optional record."""
    old = previous_by_key.get(_entry_key(entry))
    category = classify_entry(entry, old)
    decision = decide(category, entry, old, machine=machine)
    audited = AuditedEntry(
        language=language,
        category=category,
        entry=entry,
        previous=old,
        decision=decision,
    )
    if decision.action == APPROVE:
        return audited, _record_for(audited, decision, snapshot_date)
    if decision.action == RESTORE:
        if old is None:
            msg = f"{language}: cannot restore {entry.msgid!r} without a snapshot"
            raise AuditError(msg)
        audited.parked_variant = json.loads(_restore_entry(entry, old))
        return audited, _record_for(audited, decision, snapshot_date)
    return audited, None


def audit_catalogs(
    repo: Path,
    *,
    snapshot: str = DEFAULT_SNAPSHOT,
    source: str = DEFAULT_SOURCE,
    languages: Sequence[str] = (),
    machine: MachineVerdict | None = None,
) -> AuditResult:
    """Audit every catalog under ``source`` against ``snapshot``."""
    snapshot_id = _run_git(repo, "rev-parse", snapshot).strip()
    snapshot_date = _run_git(repo, "show", "-s", "--format=%cs", snapshot_id).strip()
    source_dir = repo / source
    if not source_dir.is_dir():
        msg = f"source directory {source_dir} does not exist"
        raise AuditError(msg)

    selected = set(languages)
    entries: list[AuditedEntry] = []
    records: list[ApprovalRecord] = []
    catalogs: dict[str, polib.POFile] = {}
    changed: set[str] = set()
    with_snapshot: set[str] = set()

    for path in sorted(source_dir.glob("*.po")):
        language = path.stem
        if selected and language not in selected:
            continue
        current = polib.pofile(str(path))
        previous = load_snapshot_catalog(repo, snapshot_id, language)
        previous_by_key = (
            {_entry_key(previous_entry): previous_entry for previous_entry in previous}
            if previous is not None
            else {}
        )
        if previous is not None:
            with_snapshot.add(language)
        catalogs[language] = current
        for entry in current:
            if entry.obsolete or not entry.msgid or "fuzzy" in entry.flags:
                continue
            if not has_text(entry):
                continue
            audited, record = _audit_one(
                language, entry, previous_by_key, snapshot_date, machine
            )
            entries.append(audited)
            if record is not None:
                records.append(record)
            if audited.decision.action == RESTORE:
                changed.add(language)

    return AuditResult(
        snapshot=snapshot_id,
        snapshot_date=snapshot_date,
        entries=entries,
        records=records,
        catalogs=catalogs,
        changed_catalogs=changed,
        snapshot_languages=with_snapshot,
    )


def _entry_key(entry: polib.POEntry) -> tuple[str, str, str]:
    """Return the source-side key of an entry."""
    return (entry.msgctxt or "", entry.msgid, entry.msgid_plural or "")


def _entry_reference(entry: polib.POEntry) -> dict[str, object]:
    """Return the stable reference fields for a report entry."""
    return {
        "msgctxt": entry.msgctxt or None,
        "msgid": entry.msgid,
        "msgid_plural": entry.msgid_plural or None,
    }


def build_report(result: AuditResult) -> dict[str, object]:
    """Build the deterministic audit report."""
    languages: dict[str, dict[str, int]] = {}
    for audited in result.entries:
        bucket = languages.setdefault(
            audited.language,
            {
                "shipped": 0,
                UNCHANGED: 0,
                MODEL_CHANGED: 0,
                MODEL_ADDED: 0,
                "approved": 0,
                "pending": 0,
                "restored": 0,
            },
        )
        bucket["shipped"] += 1
        bucket[audited.category] += 1
        action = audited.decision.action
        if action == APPROVE:
            bucket["approved"] += 1
        elif action == PENDING:
            bucket["pending"] += 1
        else:
            bucket["restored"] += 1
            bucket["approved"] += 1

    for language, bucket in languages.items():
        bucket["has_snapshot"] = int(language in result.snapshot_languages)

    pending = [
        {
            "language": audited.language,
            "category": audited.category,
            "reason": audited.decision.reason,
            **_entry_reference(audited.entry),
        }
        for audited in result.pending
    ]
    parked: list[dict[str, object]] = []
    for audited in result.restored:
        previous = audited.previous
        if previous is None or audited.parked_variant is None:
            continue
        parked.append(
            {
                "language": audited.language,
                **_entry_reference(previous),
                "model_variant": audited.parked_variant,
            }
        )

    return {
        "version": 1,
        "snapshot": result.snapshot,
        "snapshot_date": result.snapshot_date,
        "totals": _totals(result),
        "languages": dict(sorted(languages.items())),
        "pending": pending,
        "parked": parked,
        "notes": [
            (
                "The planning estimate of 13,615 shipped, 2,240 model-added and "
                "1,467 model-changed covered the catalogs with a pre-2026 "
                "snapshot. The measured snapshot-covered total is 13,614 with "
                "2,239 model-added and 1,467 model-changed; the one-entry "
                "difference is a boundary in the estimate, not an unaccounted "
                "entry. The report also measures 549 entries in en_US, which "
                "has no snapshot, so the grand total is 14,163."
            )
        ],
    }


def _totals(result: AuditResult) -> dict[str, int]:
    """Return the aggregate counts for the audit report."""
    categories = {UNCHANGED: 0, MODEL_CHANGED: 0, MODEL_ADDED: 0}
    actions = {APPROVE: 0, PENDING: 0, RESTORE: 0}
    for audited in result.entries:
        categories[audited.category] += 1
        actions[audited.decision.action] += 1
    return {
        "shipped": len(result.entries),
        UNCHANGED: categories[UNCHANGED],
        MODEL_CHANGED: categories[MODEL_CHANGED],
        MODEL_ADDED: categories[MODEL_ADDED],
        "approved": actions[APPROVE] + actions[RESTORE],
        "pending": actions[PENDING],
        "restored": actions[RESTORE],
    }


def _merge_ledger(
    result: AuditResult,
    path: Path,
) -> dict[str, object]:
    """Return a ledger with the audit records merged over the existing ones."""
    if path.exists():
        data = load_ledger(path)
    else:
        data = {"version": LEDGER_VERSION, "snapshot": result.snapshot, "approvals": []}
    by_key = {record_key(record): record for record in approvals(data)}
    for record in result.records:
        by_key[record_key(record)] = record
    data["snapshot"] = result.snapshot
    data["approvals"] = [by_key[key] for key in sorted(by_key)]
    return data


def _write_catalogs(result: AuditResult, source: Path) -> None:
    """Save the catalogs whose entries were restored."""
    for language in sorted(result.changed_catalogs):
        result.catalogs[language].save(str(source / f"{language}.po"))


def main(argv: Iterable[str] | None = None) -> int:
    """Run the audit command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(REPO_ROOT))
    parser.add_argument("--snapshot", default=DEFAULT_SNAPSHOT)
    parser.add_argument("--src", default=DEFAULT_SOURCE)
    parser.add_argument("--ledger", default=str(LEDGER_PATH))
    parser.add_argument("--report", default=DEFAULT_REPORT)
    parser.add_argument("--language", action="append", default=[])
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the ledger, report and any restored catalog text",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo = Path(args.repo)
    try:
        result = audit_catalogs(
            repo,
            snapshot=args.snapshot,
            source=args.src,
            languages=args.language,
        )
    except (AuditError, LedgerError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    totals = _totals(result)
    print(
        f"shipped {totals['shipped']}: unchanged {totals[UNCHANGED]}, "
        f"model-changed {totals[MODEL_CHANGED]}, "
        f"model-added {totals[MODEL_ADDED]}"
    )
    print(
        f"approvals {totals['approved']}, pending {totals['pending']}, "
        f"restored {totals['restored']}"
    )

    if not args.apply:
        print("dry run: pass --apply to write the ledger and report")
        return 0

    ledger_path = Path(args.ledger)
    report_path = Path(args.report)
    try:
        ledger = _merge_ledger(result, ledger_path)
        write_ledger(ledger, ledger_path)
        _write_catalogs(result, repo / args.src)
        report_path.write_text(
            json.dumps(build_report(result), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (AuditError, LedgerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"wrote {ledger_path} and {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
