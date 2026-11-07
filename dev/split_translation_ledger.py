"""Split the legacy translation ledger and compact its evidence.

Reads the single ``po/translation-approvals.json`` file, writes the
``po/approvals`` directory described in the ledger-split design, moves full
evidence and call payloads into the content-addressed sidecar, and verifies
that every approval key and translation digest survives.

The command is a dry run unless ``--write`` is given.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from translation_ledger import (
    APPROVALS_DIR,
    EVIDENCE_PATH,
    LEGACY_LEDGER_PATH,
    LedgerError,
    approvals,
    compact_approval_record,
    compact_operational_record,
    load_evidence,
    load_ledger,
    record_key,
    section,
    validate_ledger,
    write_ledger,
)

SECTION_KINDS = {
    "qualifications": "qualification",
    "drift_excursions": "drift",
    "gate_runs": "gate_run",
}


class MigrationError(Exception):
    """A migration that cannot continue."""


def _compact(data: dict[str, object], evidence_path: Path) -> None:
    """Compact every approval and call-bearing operational record in place."""
    approval_records = data.get("approvals", [])
    if isinstance(approval_records, list):
        for record in approval_records:
            if isinstance(record, dict):
                compact_approval_record(record, evidence_path)
    for section_name, kind in SECTION_KINDS.items():
        for record in section(data, section_name):
            if "calls" in record:
                compact_operational_record(record, evidence_path, kind=kind)


def _verify(
    old: dict[str, object],
    directory: Path,
    evidence_path: Path,
) -> None:
    """Verify that the split ledger preserves the legacy approval set."""
    new = load_ledger(directory)
    old_by_key = {record_key(record): record for record in approvals(old)}
    new_by_key = {record_key(record): record for record in approvals(new)}
    if old_by_key.keys() != new_by_key.keys():
        msg = "approval keys changed during migration"
        raise LedgerError(msg)
    for key, old_record in old_by_key.items():
        new_record = new_by_key[key]
        if old_record.get("translation_sha256") != new_record.get("translation_sha256"):
            msg = f"translation digest changed for {key!r}"
            raise LedgerError(msg)
        digest = new_record.get("evidence_sha256")
        if not isinstance(digest, str) or load_evidence(digest, evidence_path) is None:
            msg = f"evidence missing for {key!r}"
            raise LedgerError(msg)
    for section_name, kind in SECTION_KINDS.items():
        for record in section(new, section_name):
            digest = record.get("evidence_sha256")
            if digest is None:
                continue
            if (
                not isinstance(digest, str)
                or load_evidence(digest, evidence_path) is None
            ):
                msg = f"evidence missing for {kind} record"
                raise LedgerError(msg)
    print(
        f"verified {len(old_by_key)} approvals, "
        f"{len(section(new, 'qualifications'))} qualifications, "
        f"{len(section(new, 'gate_runs'))} gate runs"
    )


def _load_source(source: Path) -> dict[str, object]:
    """Read and validate the legacy ledger."""
    if not source.exists():
        msg = f"ledger {source} does not exist"
        raise MigrationError(msg)
    try:
        raw = source.read_text(encoding="utf-8")
    except OSError as error:
        msg = f"cannot read {source}: {error}"
        raise MigrationError(msg) from error
    try:
        return validate_ledger(json.loads(raw), source=str(source))
    except (json.JSONDecodeError, LedgerError) as error:
        msg = str(error)
        raise MigrationError(msg) from error


def _migrate(
    source: Path,
    directory: Path,
    evidence_path: Path,
    *,
    write: bool,
) -> int:
    """Run the split migration, optionally writing the result."""
    if directory.exists():
        if source.exists():
            print(
                f"error: migration target {directory} already exists; "
                "remove it or choose another directory",
                file=sys.stderr,
            )
            return 1
        print(f"already migrated: {directory} exists")
        return 0
    try:
        data = _load_source(source)
    except MigrationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(
        f"read {len(approvals(data))} approvals, "
        f"{len(section(data, 'qualifications'))} qualifications, "
        f"{len(section(data, 'gate_runs'))} gate runs"
    )
    if not write:
        print("dry run: pass --write to create the split ledger")
        return 0
    compacted = dict(data)
    compacted["approvals"] = [dict(record) for record in approvals(data)]
    for section_name in SECTION_KINDS:
        compacted[section_name] = [
            dict(record) for record in section(data, section_name)
        ]
    _compact(compacted, evidence_path)
    created = not directory.exists()
    try:
        write_ledger(compacted, directory)
        _verify(data, directory, evidence_path)
        source.unlink()
    except (LedgerError, OSError) as error:
        print(f"error: migration failed: {error}", file=sys.stderr)
        if created and directory.exists():
            shutil.rmtree(directory)
        return 1
    print(f"wrote {directory} and removed {source}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the migration command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=LEGACY_LEDGER_PATH)
    parser.add_argument("--directory", type=Path, default=APPROVALS_DIR)
    parser.add_argument("--evidence", type=Path, default=EVIDENCE_PATH)
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the split ledger and remove the legacy file",
    )
    args = parser.parse_args(argv)
    try:
        return _migrate(
            args.source,
            args.directory,
            args.evidence,
            write=args.write,
        )
    except LedgerError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
