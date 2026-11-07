"""Compile .po files into .mo files.

Usage:
  python3 compile_mo.py # compiles po/scantpaper/*.po into src/scantpaper/locale/<lang>/LC_MESSAGES/<domain>.mo
  python3 compile_mo.py --src po/scantpaper --out src/scantpaper/locale
  python3 compile_mo.py --src po/scantpaper --out src/scantpaper/locale --domain scantpaper
  python3 compile_mo.py --approvals po/approvals

With ``--approvals`` only entries that carry a valid approval are compiled; an
unapproved non-fuzzy entry is blanked so gettext falls back to its English
source. Without the option every non-fuzzy entry compiles as before, which
keeps local previews and existing tests unchanged.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import polib
from summarise_po import template_keys
from translation_ledger import (
    LedgerError,
    approval_for_entry,
    load_ledger,
)


def guess_lang_and_domain(
    po_file: Path, given_domain: str | None = None
) -> tuple[str, str]:
    """Infer language and domain from a Rosetta-layout file path.

    A template directory holds one template's files, so the directory name is
    the domain and the file stem is the language, e.g. ``po/scantpaper/de.po``
    -> domain ``scantpaper``, language ``de``. ``given_domain`` overrides the
    domain when supplied.
    """
    lang = po_file.stem
    domain = given_domain or po_file.parent.name
    return domain, lang


def has_translation(entry: polib.POEntry) -> bool:
    """Return whether an entry carries a usable translation."""
    if entry.msgid_plural:
        return any(value.strip() for value in (entry.msgstr_plural or {}).values())
    return bool(entry.msgstr.strip())


def filter_unapproved(
    po: polib.POFile,
    ledger: dict[str, object],
    language: str,
) -> int:
    """Blank every non-fuzzy entry without a valid approval; return the count.

    A fuzzy entry is left alone because ``polib.save_as_mofile`` drops it
    anyway. An empty translation is already an English fallback, so it is not
    counted as dropped.
    """
    dropped = 0
    for entry in po:
        if entry.obsolete or not entry.msgid or "fuzzy" in entry.flags:
            continue
        if not has_translation(entry):
            continue
        if approval_for_entry(ledger, language, entry) is not None:
            continue
        entry.msgstr = ""
        entry.msgstr_plural = {}
        dropped += 1
    return dropped


def report_language(
    po: polib.POFile,
    ledger: dict[str, object],
    language: str,
    keys: set[tuple[str, str, str]],
) -> dict[str, int]:
    """Return approval, fallback and coverage counts for one catalog."""
    approved = fallback = fuzzy = untranslated = 0
    catalog_keys: set[tuple[str, str, str]] = set()
    for entry in po:
        if entry.obsolete or not entry.msgid:
            continue
        catalog_keys.add((entry.msgctxt or "", entry.msgid, entry.msgid_plural or ""))
        if "fuzzy" in entry.flags:
            fuzzy += 1
        elif not has_translation(entry):
            untranslated += 1
        elif approval_for_entry(ledger, language, entry) is not None:
            approved += 1
        else:
            fallback += 1
    return {
        "approved": approved,
        "fallback": fallback,
        "fuzzy": fuzzy,
        "untranslated": untranslated,
        "missing": len(keys - catalog_keys),
        "stale": len(catalog_keys - keys),
    }


class CompileError(Exception):
    """A compile input that can be reported without a traceback."""


def load_approvals(path: Path | None) -> dict[str, object] | None:
    """Load the approval ledger, or return None when it was not requested."""
    if path is None:
        return None
    try:
        return load_ledger(path)
    except LedgerError as error:
        raise CompileError(str(error)) from error


def resolve_pot(src: Path, explicit: Path | None, *, required: bool) -> Path | None:
    """Resolve the coverage template, optionally finding one under ``src``."""
    if explicit is not None:
        return explicit
    if not required:
        return None
    templates = sorted(src.rglob("*.pot"))
    if not templates:
        msg = f"no .pot template found under {src}"
        raise CompileError(msg)
    return templates[0]


def compile_catalog(
    po_path: Path,
    ledger: dict[str, object] | None,
    keys: set[tuple[str, str, str]],
    out_dir: Path,
    domain_override: str | None,
) -> tuple[str, dict[str, int] | None]:
    """Compile one catalog and return its language and approval stats."""
    domain, lang = guess_lang_and_domain(po_path, domain_override)
    mo_path = out_dir / lang / "LC_MESSAGES" / f"{domain}.mo"
    print(f"Compiling {po_path} -> {mo_path} (domain={domain}, lang={lang})")
    mo_path.parent.mkdir(parents=True, exist_ok=True)
    po = polib.pofile(str(po_path))

    stats: dict[str, int] | None = None
    if ledger is not None:
        stats = report_language(po, ledger, lang, keys)
        dropped = filter_unapproved(po, ledger, lang)
        print(
            f"{lang}: {stats['approved']} approved, "
            f"{stats['fallback']} unapproved entries fall back to English, "
            f"{stats['missing']} missing from the template"
        )
        if dropped != stats["fallback"]:  # pragma: no cover - invariant
            msg = f"{lang}: counted {stats['fallback']} fallbacks but dropped {dropped}"
            raise CompileError(msg)

    po.save_as_mofile(str(mo_path))
    return lang, stats


def write_report(
    path: Path,
    approvals: Path | None,
    pot: Path | None,
    template_count: int,
    languages: dict[str, dict[str, int]],
) -> None:
    """Write the per-language coverage and fallback report."""
    payload = {
        "approvals": str(approvals) if approvals is not None else None,
        "pot": str(pot) if pot is not None else None,
        "template_msgids": template_count,
        "languages": languages,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {path}")


def main() -> None:
    """Run the application entry point."""
    p = argparse.ArgumentParser(description="Compile .po to .mo")
    p.add_argument(
        "--src",
        default="po/scantpaper",
        help="Source dir containing .po files (default: po/scantpaper)",
    )
    p.add_argument(
        "--out",
        default="src/scantpaper/locale",
        help="Output locale dir (default: src/scantpaper/locale)",
    )
    p.add_argument(
        "--domain",
        default=None,
        help="Force domain for output (default: inferred from filename or 'messages')",
    )
    p.add_argument(
        "--pattern",
        default="*.po",
        help="Glob pattern for .po files under --src (default: *.po)",
    )
    p.add_argument(
        "--approvals",
        type=Path,
        help="Compile only entries with a valid approval in this ledger",
    )
    p.add_argument(
        "--pot",
        type=Path,
        help="Template used for the coverage report (default: find a .pot under --src)",
    )
    p.add_argument(
        "--report",
        type=Path,
        help="Write per-language coverage and fallback counts as JSON",
    )
    args = p.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"Source dir '{src}' does not exist.", file=sys.stderr)
        sys.exit(1)

    try:
        ledger = load_approvals(args.approvals)
    except CompileError as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
    if args.report is not None and ledger is None:
        print("error: --report requires --approvals", file=sys.stderr)
        sys.exit(1)
    try:
        pot_path = resolve_pot(src, args.pot, required=args.report is not None)
    except CompileError as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)

    po_files = list(src.rglob(args.pattern))
    if not po_files:
        print("No .po files found.", file=sys.stderr)
        sys.exit(0)

    keys = template_keys(pot_path) if pot_path is not None else set()
    language_report: dict[str, dict[str, int]] = {}
    out_dir = Path(args.out)
    for po_path in po_files:
        lang, stats = compile_catalog(po_path, ledger, keys, out_dir, args.domain)
        if stats is not None:
            language_report[lang] = stats

    if args.report is not None:
        write_report(
            args.report,
            args.approvals,
            pot_path,
            len(keys),
            language_report,
        )


if __name__ == "__main__":
    main()
