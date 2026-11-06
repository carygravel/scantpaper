"""Tests for template-relative coverage in dev/summarise_po.py."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import polib

REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARISE = REPO_ROOT / "dev" / "summarise_po.py"

CATALOG_ENTRIES = 558
SHIPPED = 549
FUZZY = CATALOG_ENTRIES - SHIPPED
STALE = 24
SHARED = CATALOG_ENTRIES - STALE
TEMPLATE_ENTRIES = 665
MISSING = TEMPLATE_ENTRIES - SHARED


def _write_catalog(path: Path, msgids: list[str], *, fuzzy: set[str]) -> None:
    """Write a catalog with the given msgids and fuzzy flags."""
    po = polib.POFile()
    po.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
    }
    for msgid in msgids:
        entry = polib.POEntry(msgid=msgid, msgstr=f"translated {msgid}")
        if msgid in fuzzy:
            entry.flags.append("fuzzy")
        po.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(path))


def _write_template(path: Path, msgids: list[str]) -> None:
    """Write a message template with the given msgids."""
    po = polib.POFile()
    po.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
    }
    for msgid in msgids:
        po.append(polib.POEntry(msgid=msgid, msgstr=""))
    path.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(path))


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Build the 558-entry catalog and 665-msgid template from the task."""
    shared = [f"shared {index}" for index in range(SHARED)]
    stale = [f"stale {index}" for index in range(STALE)]
    current = shared + stale
    template = shared + [f"new {index}" for index in range(MISSING)]

    src = tmp_path / "po" / "scantpaper"
    _write_catalog(
        src / "de.po",
        current,
        fuzzy=set(current[SHIPPED:]),
    )
    pot = src / "scantpaper.pot"
    _write_template(pot, template)
    return src, pot


def test_coverage_is_measured_against_the_template(tmp_path: Path) -> None:
    """The denominator is the template, not the catalog's own entries."""
    src, pot = _fixture(tmp_path)
    result = subprocess.run(
        [
            "python3",
            str(SUMMARISE),
            "--src",
            str(src),
            "--pot",
            str(pot),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["template_msgids"] == TEMPLATE_ENTRIES
    coverage = payload["languages"]["de"]
    assert coverage["shipped"] == SHIPPED
    assert coverage["fuzzy"] == FUZZY
    assert coverage["missing"] == MISSING
    assert coverage["stale"] == STALE


def test_text_report_names_the_template_denominator(tmp_path: Path) -> None:
    """The table shows 549 of 665 rather than 549 of 558."""
    src, pot = _fixture(tmp_path)
    result = subprocess.run(
        ["python3", str(SUMMARISE), "--src", str(src), "--pot", str(pot)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert f"{SHIPPED}/{TEMPLATE_ENTRIES}" in result.stdout
    assert f"{SHIPPED}/{CATALOG_ENTRIES}" not in result.stdout


def test_without_pot_the_catalog_view_is_unchanged(tmp_path: Path) -> None:
    """The legacy per-catalog summary still reports 549 shipped and 9 fuzzy."""
    src, _ = _fixture(tmp_path)
    result = subprocess.run(
        ["python3", str(SUMMARISE), "--src", str(src), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    row = json.loads(result.stdout)["languages"][0]
    assert row["non_fuzzy"] == SHIPPED
    assert row["fuzzy"] == FUZZY
    assert row["untranslated"] == 0
