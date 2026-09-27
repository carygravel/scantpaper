"""Summarise translation coverage across the .po catalogs.

Usage:
  python3 dev/summarise_po.py        # summarise po/scantpaper/*.po
  python3 dev/summarise_po.py --src po/scantpaper

Prints one row per language with the counts of non-fuzzy (shipped), fuzzy
(awaiting review) and untranslated strings, sorted by the number of
non-fuzzy strings descending.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polib


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


def main() -> None:
    """Run the application entry point."""
    parser = argparse.ArgumentParser(description="Summarise catalog coverage")
    parser.add_argument(
        "--src",
        default="po/scantpaper",
        help="Source dir containing .po files (default: po/scantpaper)",
    )
    args = parser.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"Source dir '{src}' does not exist.", file=sys.stderr)
        sys.exit(1)

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
