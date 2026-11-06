"""Tests for approval-filtered compilation in dev/compile_mo.py."""

from __future__ import annotations

import gettext
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import polib

if TYPE_CHECKING:
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "dev"
COMPILE = DEV_DIR / "compile_mo.py"

sys.path.insert(0, str(DEV_DIR))


def _load_ledger() -> ModuleType:
    """Import the ledger helper used to build a fixture."""
    spec = importlib.util.spec_from_file_location(
        "translation_ledger", str(DEV_DIR / "translation_ledger.py")
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["translation_ledger"] = module
    spec.loader.exec_module(module)
    return module


LEDGER = _load_ledger()


def _write_catalog(path: Path) -> None:
    """Write a catalog with approved, unapproved and fuzzy entries."""
    po = polib.POFile()
    po.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
    }
    po.append(polib.POEntry(msgid="Approved", msgstr="Genehmigt"))
    po.append(polib.POEntry(msgid="Unapproved", msgstr="Nicht genehmigt"))
    fuzzy = polib.POEntry(msgid="Fuzzy", msgstr="Unscharf")
    fuzzy.flags.append("fuzzy")
    po.append(fuzzy)
    path.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(path))


def _write_ledger(path: Path, catalog: Path) -> None:
    """Approve only the `Approved` entry."""
    po = polib.pofile(str(catalog))
    entry = po.find("Approved")
    assert entry is not None
    record = LEDGER.make_record(
        "de",
        entry,
        "human-historical",
        context=LEDGER.ApprovalContext(approval_date="2026-01-01"),
    )
    LEDGER.write_ledger(
        {"version": 1, "snapshot": "a" * 40, "approvals": [record]}, path
    )


def _compile(src: Path, out: Path, ledger: Path | None = None) -> None:
    """Run compile_mo.py over a fixture."""
    command = [
        "python3",
        str(COMPILE),
        "--src",
        str(src),
        "--out",
        str(out),
    ]
    if ledger is not None:
        command += ["--approvals", str(ledger)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def _translations(out: Path) -> gettext.GNUTranslations:
    """Load the compiled German catalog."""
    mo = out / "de" / "LC_MESSAGES" / "scantpaper.mo"
    with mo.open("rb") as handle:
        return gettext.GNUTranslations(handle)


def test_approved_entry_compiles_and_unapproved_falls_back(tmp_path: Path) -> None:
    """Only an approved non-fuzzy translation reaches the .mo."""
    src = tmp_path / "po" / "scantpaper"
    catalog = src / "de.po"
    _write_catalog(catalog)
    ledger = tmp_path / "approvals.json"
    _write_ledger(ledger, catalog)

    out = tmp_path / "locale"
    _compile(src, out, ledger)
    translations = _translations(out)

    assert translations.gettext("Approved") == "Genehmigt"
    assert translations.gettext("Unapproved") == "Unapproved"
    assert translations.gettext("Fuzzy") == "Fuzzy"


def test_without_approvals_every_non_fuzzy_entry_compiles(tmp_path: Path) -> None:
    """The legacy path is unchanged when --approvals is absent."""
    src = tmp_path / "po" / "scantpaper"
    _write_catalog(src / "de.po")
    out = tmp_path / "locale"
    _compile(src, out)

    translations = _translations(out)
    assert translations.gettext("Approved") == "Genehmigt"
    assert translations.gettext("Unapproved") == "Nicht genehmigt"
    assert translations.gettext("Fuzzy") == "Fuzzy"


def test_edited_translation_loses_its_approval(tmp_path: Path) -> None:
    """A stale digest does not approve the edited text."""
    src = tmp_path / "po" / "scantpaper"
    catalog = src / "de.po"
    _write_catalog(catalog)
    ledger = tmp_path / "approvals.json"
    _write_ledger(ledger, catalog)

    po = polib.pofile(str(catalog))
    approved = po.find("Approved")
    assert approved is not None
    approved.msgstr = "Geändert"
    po.save(str(catalog))

    out = tmp_path / "locale"
    _compile(src, out, ledger)
    assert _translations(out).gettext("Approved") == "Approved"


def test_report_names_template_coverage_and_fallbacks(tmp_path: Path) -> None:
    """The report uses the template denominator and names missing entries."""
    src = tmp_path / "po" / "scantpaper"
    src.mkdir(parents=True)
    catalog = src / "de.po"
    pot = src / "scantpaper.pot"
    _write_catalog(catalog)
    po = polib.pofile(str(catalog))
    po.append(polib.POEntry(msgid="Stale", msgstr="Veraltet"))
    po.save(str(catalog))

    template = polib.POFile()
    template.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
    }
    for msgid in ("Approved", "Unapproved", "Missing"):
        template.append(polib.POEntry(msgid=msgid, msgstr=""))
    template.save(str(pot))

    ledger = tmp_path / "approvals.json"
    _write_ledger(ledger, catalog)
    out = tmp_path / "locale"
    report = tmp_path / "translation-report.json"
    result = subprocess.run(
        [
            "python3",
            str(COMPILE),
            "--src",
            str(src),
            "--out",
            str(out),
            "--approvals",
            str(ledger),
            "--pot",
            str(pot),
            "--report",
            str(report),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["template_msgids"] == 3
    german = payload["languages"]["de"]
    assert german["approved"] == 1
    assert german["fallback"] == 2
    assert german["missing"] == 1
    assert german["stale"] == 2
    assert "de" in payload["languages"]
