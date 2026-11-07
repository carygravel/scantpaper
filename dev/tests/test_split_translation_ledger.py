"""Tests for dev/split_translation_ledger.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

import polib

if TYPE_CHECKING:
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "dev"
sys.path.insert(0, str(DEV_DIR))


def _load(name: str) -> ModuleType:
    """Import one dev module with its sibling imports available."""
    path = DEV_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


LEDGER = _load("translation_ledger")
SPLIT = _load("split_translation_ledger")


def _legacy(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Write a small legacy ledger and return the migration paths."""
    entry = polib.POEntry(msgid="Delete", msgstr="Löschen")
    record = cast(
        "dict[str, object]",
        LEDGER.make_record(
            "de",
            entry,
            "human-historical",
            context=LEDGER.ApprovalContext(approval_date="2026-02-28"),
        ),
    )
    data: dict[str, object] = {
        "version": 1,
        "snapshot": "a" * 40,
        "approvals": [record],
        "qualifications": [
            {
                "release": "r1",
                "language": "de",
                "score": 1.0,
                "calls": [{"cost_usd": 0.1}],
                "call_count": 1,
                "total_cost_usd": 0.1,
                "latency_ms": 1.0,
            }
        ],
        "gate_runs": [
            {
                "language": "de",
                "outcome": "approved",
                "calls": [{"cost_usd": 0.1}],
                "call_count": 1,
                "total_cost_usd": 0.1,
                "latency_ms": 1.0,
            }
        ],
    }
    source = tmp_path / "translation-approvals.json"
    LEDGER.write_ledger(data, source)
    return source, tmp_path / "approvals", tmp_path / "evidence.ndjson"


def test_migration_writes_and_verifies_the_split_tree(tmp_path: Path) -> None:
    """The migration writes the tree, sidecar and removes the old file."""
    source, directory, evidence = _legacy(tmp_path)
    assert (
        SPLIT.main(
            [
                "--source",
                str(source),
                "--directory",
                str(directory),
                "--evidence",
                str(evidence),
                "--write",
            ]
        )
        == 0
    )
    assert not source.exists()
    assert (directory / "manifest.json").exists()
    assert (directory / "global.json").exists()
    assert (directory / "de.json").exists()
    assert evidence.exists()
    merged = LEDGER.load_ledger(directory)
    record = LEDGER.approvals(merged)[0]
    assert record["evidence_sha256"]
    assert (
        LEDGER.load_evidence(cast("str", record["evidence_sha256"]), evidence)
        is not None
    )
    qualification = LEDGER.section(merged, "qualifications")[0]
    assert "calls" not in qualification
    gate_run = LEDGER.section(merged, "gate_runs")[0]
    assert "calls" not in gate_run


def test_migration_is_idempotent_and_dry_run_writes_nothing(tmp_path: Path) -> None:
    """A second run reports already migrated; a dry run leaves the old file."""
    source, directory, evidence = _legacy(tmp_path)
    assert (
        SPLIT.main(
            [
                "--source",
                str(source),
                "--directory",
                str(directory),
                "--evidence",
                str(evidence),
            ]
        )
        == 0
    )
    assert source.exists()
    assert not directory.exists()
    assert not evidence.exists()

    assert (
        SPLIT.main(
            [
                "--source",
                str(source),
                "--directory",
                str(directory),
                "--evidence",
                str(evidence),
                "--write",
            ]
        )
        == 0
    )
    assert (
        SPLIT.main(
            [
                "--source",
                str(source),
                "--directory",
                str(directory),
                "--evidence",
                str(evidence),
                "--write",
            ]
        )
        == 0
    )
