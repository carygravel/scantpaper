"""Summarise translation coverage across the .po catalogs.

Usage:
  python3 dev/summarise_po.py        # summarise po/scantpaper/*.po
  python3 dev/summarise_po.py --src po/scantpaper
  python3 dev/summarise_po.py --pot po/scantpaper/scantpaper.pot --json

Without ``--pot`` it prints the catalog's own non-fuzzy, fuzzy and untranslated
counts. With ``--pot`` it measures coverage against the current template, so an
out-of-date catalog cannot report a denominator that hides its missing strings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TypedDict

import polib

EntryKey = tuple[str, str, str]


class Coverage(TypedDict):
    """Coverage counts for one catalog against the current template."""

    shipped: int
    fuzzy: int
    missing: int
    stale: int
    obsolete: int
    untranslated: int


def entry_key(entry: polib.POEntry) -> EntryKey:
    """Return the source-side key of an entry."""
    return (entry.msgctxt or "", entry.msgid, entry.msgid_plural or "")


def has_translation(entry: polib.POEntry) -> bool:
    """Return whether an entry carries a usable translation.

    Plural entries keep their strings in ``msgstr_plural`` while the singular
    ``msgstr`` stays empty, so a summary must not treat a filled plural form
    as untranslated.
    """
    if entry.msgid_plural:
        return any(value.strip() for value in (entry.msgstr_plural or {}).values())
    return bool(entry.msgstr.strip())


def counts(path: Path) -> tuple[str, int, int, int]:
    """Return (language, non_fuzzy, fuzzy, untranslated) for one catalog."""
    po = polib.pofile(str(path))
    non_fuzzy = fuzzy = untranslated = 0
    for entry in po:
        if entry.obsolete or not entry.msgid:
            continue
        if "fuzzy" in entry.flags:
            fuzzy += 1
        elif has_translation(entry):
            non_fuzzy += 1
        else:
            untranslated += 1
    return path.stem, non_fuzzy, fuzzy, untranslated


def template_keys(path: Path) -> set[EntryKey]:
    """Return the active, non-header keys of a message template."""
    return {
        entry_key(entry)
        for entry in polib.pofile(str(path))
        if not entry.obsolete and entry.msgid
    }


def coverage_counts(path: Path, keys: set[EntryKey]) -> tuple[str, Coverage]:
    """Return coverage for one catalog against the template keys."""
    po = polib.pofile(str(path))
    catalog_keys: set[EntryKey] = set()
    shipped = fuzzy = untranslated = 0
    for entry in po:
        if entry.obsolete or not entry.msgid:
            continue
        catalog_keys.add(entry_key(entry))
        if "fuzzy" in entry.flags:
            fuzzy += 1
        elif has_translation(entry):
            shipped += 1
        else:
            untranslated += 1
    return path.stem, Coverage(
        shipped=shipped,
        fuzzy=fuzzy,
        missing=len(keys - catalog_keys),
        stale=len(catalog_keys - keys),
        obsolete=len(po.obsolete_entries()),
        untranslated=untranslated,
    )


def coverage_payload(src: Path, pot: Path) -> dict[str, object]:
    """Build the JSON payload for template-relative coverage."""
    keys = template_keys(pot)
    languages: dict[str, Coverage] = {}
    for path in sorted(src.glob("*.po")):
        language, language_coverage = coverage_counts(path, keys)
        languages[language] = language_coverage
    return {
        "pot": str(pot),
        "template_msgids": len(keys),
        "languages": languages,
    }


def print_coverage(payload: dict[str, object]) -> None:
    """Print the human-readable coverage table."""
    languages = payload["languages"]
    if not isinstance(languages, dict):
        return
    total_value = payload["template_msgids"]
    total = total_value if isinstance(total_value, int) else 0
    rows = sorted(
        (
            language,
            coverage["shipped"],
            coverage["fuzzy"],
            coverage["missing"],
            coverage["stale"],
            coverage["obsolete"],
        )
        for language, coverage in languages.items()
        if isinstance(coverage, dict)
    )
    width = max(len(str(row[0])) for row in rows) if rows else 4
    header = (
        f"{'lang':<{width}}  {'shipped':>7}/{total:<7}  {'fuzzy':>5}  "
        f"{'missing':>7}  {'stale':>5}  {'obsolete':>8}"
    )
    print(header)
    print("-" * len(header))
    totals = [0, 0, 0, 0, 0]
    for language, shipped, fuzzy, missing, stale, obsolete in rows:
        print(
            f"{language:<{width}}  {shipped:>7}/{total:<7}  {fuzzy:>5}  "
            f"{missing:>7}  {stale:>5}  {obsolete:>8}"
        )
        for index, value in enumerate((shipped, fuzzy, missing, stale, obsolete)):
            totals[index] += value
    print("-" * len(header))
    print(
        f"{'TOTAL':<{width}}  {totals[0]:>7}/{total:<7}  {totals[1]:>5}  "
        f"{totals[2]:>7}  {totals[3]:>5}  {totals[4]:>8}"
    )


def main() -> None:
    """Run the application entry point."""
    parser = argparse.ArgumentParser(description="Summarise catalog coverage")
    parser.add_argument(
        "--src",
        default="po/scantpaper",
        help="Source dir containing .po files (default: po/scantpaper)",
    )
    parser.add_argument(
        "--pot",
        type=Path,
        help="Measure coverage against this template instead of the catalog",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a table",
    )
    args = parser.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"Source dir '{src}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if args.pot is not None:
        payload = coverage_payload(src, args.pot)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print_coverage(payload)
        return

    if args.json:
        rows = [
            {
                "language": language,
                "non_fuzzy": non_fuzzy,
                "fuzzy": fuzzy,
                "untranslated": untranslated,
            }
            for language, non_fuzzy, fuzzy, untranslated in (
                counts(path) for path in sorted(src.glob("*.po"))
            )
        ]
        print(json.dumps({"languages": rows}, ensure_ascii=False, indent=2))
        return

    rows = sorted(
        (counts(path) for path in sorted(src.glob("*.po"))),
        key=lambda row: row[1],
        reverse=True,
    )
    if not rows:
        print("No .po files found.", file=sys.stderr)
        sys.exit(0)

    width = max(len(row[0]) for row in rows)
    header = f"{'lang':<{width}}  {'non-fuzzy':>9}  {'fuzzy':>6}  {'untrans':>8}"
    print(header)
    print("-" * len(header))
    totals = [0, 0, 0]
    for lang, non_fuzzy, fuzzy, untranslated in rows:
        print(f"{lang:<{width}}  {non_fuzzy:9}  {fuzzy:6}  {untranslated:8}")
        totals[0] += non_fuzzy
        totals[1] += fuzzy
        totals[2] += untranslated
    print("-" * len(header))
    print(f"{'TOTAL':<{width}}  {totals[0]:9}  {totals[1]:6}  {totals[2]:8}")


if __name__ == "__main__":
    main()
