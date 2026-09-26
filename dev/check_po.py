"""Deterministic checks for translation catalogs.

For every `po/*.po` this runs `msgfmt --check` (format-specifier
consistency, escaping, plural-entry counts) and validates the catalog's
`Plural-Forms` header against the CLDR plural-form count for its language.

Exit status is non-zero if any catalog fails a check. Run in CI via
`src/scantpaper/tests/test_po_files.py`.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# CLDR plural-form count per language code. Only the well-established
# counts are enforced; the common {1,2} pair is accepted for the rest so
# that glibc/CLDR discrepancies (e.g. id, vi, fa) do not produce false
# positives.
CLDR_NPLURALS: dict[str, int] = {
    "id": 1,
    "ja": 1,
    "ko": 1,
    "vi": 1,
    "zh_CN": 1,
    "zh_TW": 1,
    "ab": 2,
    "af": 2,
    "bg": 2,
    "ca": 2,
    "da": 2,
    "de": 2,
    "el": 2,
    "en_GB": 2,
    "en_US": 2,
    "es": 2,
    "eu": 2,
    "fa": 2,
    "fi": 2,
    "fr": 2,
    "gl": 2,
    "gu": 2,
    "he": 2,
    "hi": 2,
    "hu": 2,
    "it": 2,
    "nb": 2,
    "nl": 2,
    "oc": 2,
    "pt": 2,
    "pt_BR": 2,
    "sv": 2,
    "tr": 2,
    "be": 3,
    "cs": 3,
    "hr": 3,
    "pl": 3,
    "ro": 3,
    "ru": 3,
    "sk": 3,
    "sr": 3,
    "uk": 3,
    "sl": 4,
    "ar": 6,
}


def language_from_filename(path: Path) -> str:
    """Infer the language code from a `scantpaper-<lang>.po` filename."""
    return path.name[len("scantpaper-") : -len(".po")]


def plural_forms_nplurals(po_text: str) -> int | None:
    """Extract `nplurals` from the catalog header, or None if absent."""
    match = re.search(r"nplurals=(\d+)", po_text)
    return int(match.group(1)) if match else None


def check_catalog(path: Path) -> int:
    """Check one catalog; return the number of errors found."""
    errors = 0
    lang = language_from_filename(path)

    result = subprocess.run(
        ["msgfmt", "--check", "-o", "/dev/null", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        errors += 1
        print(f"[FAIL] {path.name}: msgfmt --check\n{result.stderr.rstrip()}")

    declared = plural_forms_nplurals(path.read_text(encoding="utf-8"))
    if declared is None:
        print(f"[note] {path.name}: no Plural-Forms header declared")
    elif lang in CLDR_NPLURALS and declared != CLDR_NPLURALS[lang]:
        errors += 1
        print(
            f"[FAIL] {path.name}: Plural-Forms nplurals={declared} "
            f"but CLDR specifies {CLDR_NPLURALS[lang]} for {lang}"
        )

    return errors


def main() -> int:
    """Run the application entry point."""
    parser = argparse.ArgumentParser(description="Check translation catalogs")
    parser.add_argument("--src", default="po", help="Source dir of .po files")
    args = parser.parse_args()

    src = Path(args.src)
    total_errors = 0
    checked = 0
    for po_path in sorted(src.glob("*.po")):
        checked += 1
        total_errors += check_catalog(po_path)

    print(f"\nChecked {checked} catalogs, {total_errors} error(s).")
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
