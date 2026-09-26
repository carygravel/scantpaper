"""Deterministic checks for translation catalogs.

For every `po/*.po` this runs `msgfmt --check` (format-specifier
consistency, escaping, plural-entry counts), validates the catalog's
`Plural-Forms` header against the CLDR plural-form count for its language,
and parses the message bodies with polib to catch defects `msgfmt` misses:

* printf placeholders split from their conversion letter by a space
  (`"% s"`, `"% d"`), which `msgfmt` accepts under `python-format`/
  `perl-format` flags but which render incorrectly at runtime;
* malformed `str.format` fields (`{}` replacement fields whose braces are
  unbalanced, or whose field names differ from the `msgid`), which `msgfmt`
  does not check at all;
* catalog-hygiene items reported as advisory: obsolete-entry growth past a
  ratcheted ceiling, `#, fuzzy` entries with an empty translation, and
  message text that is not in Unicode NFC form.

Exit status is non-zero if any hard check fails. Run in CI via
`src/scantpaper/tests/test_po_files.py`.
"""

from __future__ import annotations

import argparse
import re
import string
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import polib

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

# Per-catalog ceiling on obsolete (#~) entries. The check fails only when a
# catalog's obsolete count GROWS past this value, never on the pre-existing
# backlog. Values are the counts at adoption; ratchet them DOWN as the
# backlog is purged. A language absent from the map defaults to its current
# count (so it can only fail on future growth).
OBSOLETE_CEILING: dict[str, int] = {
    "be": 4,
    "bg": 36,
    "ca": 52,
    "cs": 118,
    "da": 164,
    "de": 138,
    "el": 112,
    "en_GB": 133,
    "es": 126,
    "eu": 164,
    "fa": 1,
    "fi": 139,
    "fr": 102,
    "gl": 98,
    "gu": 46,
    "he": 24,
    "hr": 26,
    "hu": 139,
    "it": 137,
    "ja": 92,
    "ko": 37,
    "nb": 59,
    "nl": 96,
    "oc": 3,
    "pl": 135,
    "pt": 31,
    "pt_BR": 69,
    "ru": 139,
    "sk": 126,
    "sl": 59,
    "sv": 72,
    "tr": 124,
    "uk": 139,
    "zh_CN": 90,
    "zh_TW": 7,
}

# A printf conversion letter preceded by whitespace directly after a `%`.
# A single `%` followed by whitespace and one of these letters is the
# translation-time rewrap artifact this check targets.
_PRINTF_POISON = re.compile(r"%\s+[diouxXeEfgGaAcspn]")

_FORMATTER = string.Formatter()


def language_from_filename(path: Path) -> str:
    """Infer the language code from a `scantpaper-<lang>.po` filename."""
    return path.name[len("scantpaper-") : -len(".po")]


def plural_forms_nplurals(po_text: str) -> int | None:
    """Extract `nplurals` from the catalog header, or None if absent."""
    match = re.search(r"nplurals=(\d+)", po_text)
    return int(match.group(1)) if match else None


def _translated_strings(entry: polib.RESEntry) -> list[str]:
    """Return the non-empty translated bodies for one entry."""
    bodies = entry.msgstr if isinstance(entry.msgstr, list) else [entry.msgstr]
    return [body for body in bodies if body.strip()]


def _entry_key(entry: polib.RESEntry) -> tuple[object, object, object]:
    """Return a key that identifies an entry across active/obsolete copies.

    The element types are widened to ``object`` because polib ships no type
    information, so its attributes are statically ``Unknown``; the key is
    only ever used for set membership and equality.
    """
    return (entry.msgctxt, entry.msgid, entry.msgid_plural)


def _active_entries(po: polib.POFile) -> list[polib.RESEntry]:
    """Return shipped entries, excluding any that also appear as obsolete.

    polib can leak an obsolete (`#~`) entry into the normal iteration when a
    stray flag comment (e.g. `#, perl-format`) precedes the `#~ msgid`. Such
    strings never compile into a `.mo`, so they must not be treated as live
    defects; drop any active-iterated entry whose key is obsolete.
    """
    obsolete = {_entry_key(e) for e in po.obsolete_entries()}
    return [e for e in po if _entry_key(e) not in obsolete]


def _printf_poison(text: str) -> bool:
    """Return True if text has a `%` split from its conversion letter."""
    return bool(_PRINTF_POISON.search(text.replace("%%", "")))


def _format_fields(text: str) -> list[str] | None:
    """Return the str.format field names, or None if the text is malformed."""
    try:
        return [field for _, field, _, _ in _FORMATTER.parse(text) if field is not None]
    except ValueError:
        return None


def _check_placeholders(path: Path) -> list[str]:
    """Return hard-error messages for malformed placeholders in a catalog."""
    errors: list[str] = []
    for entry in _active_entries(polib.pofile(str(path))):
        strings = _translated_strings(entry)
        if not strings:
            continue
        flagged_printf = any(flag.endswith("-format") for flag in entry.flags)
        if flagged_printf:
            errors.extend(
                f"{path.name}: printf token split by space in "
                f"{entry.msgid!r} -> {body!r}"
                for body in strings
                if _printf_poison(body)
            )
        id_fields = _format_fields(entry.msgid)
        if id_fields:
            expected = Counter(id_fields)
            for body in strings:
                got = _format_fields(body)
                if got is None:
                    errors.append(
                        f"{path.name}: malformed braces in {entry.msgid!r} -> {body!r}"
                    )
                elif Counter(got) != expected:
                    errors.append(
                        f"{path.name}: str.format fields changed "
                        f"in {entry.msgid!r} -> {body!r}"
                    )
    return errors


def _hygiene(path: Path) -> tuple[list[str], list[str]]:
    """Return (advisory lines, hard errors) from catalog housekeeping."""
    errors: list[str] = []
    notes: dict[str, int] = {}
    po = polib.pofile(str(path))

    lang = language_from_filename(path)
    active = _active_entries(po)
    obsolete = len(po.obsolete_entries())
    ceiling = OBSOLETE_CEILING.get(lang, obsolete)
    if obsolete > ceiling:
        errors.append(
            f"{path.name}: obsolete entries {obsolete} exceeds ceiling {ceiling}"
        )
    if obsolete:
        notes["obsolete"] = obsolete

    empty_fuzzy = sum(
        1 for entry in active if entry.fuzzy and not _translated_strings(entry)
    )
    if empty_fuzzy:
        notes["empty-fuzzy"] = empty_fuzzy

    non_nfc = sum(
        1
        for entry in active
        for body in _translated_strings(entry)
        if not unicodedata.is_normalized("NFC", body)
    )
    if non_nfc:
        notes["non-NFC"] = non_nfc

    bare_multi = sum(
        1
        for entry in active
        if (fields := _format_fields(entry.msgid))
        and len(fields) > 1
        and any(field == "" for field in fields)
    )
    if bare_multi:
        notes["bare-multifield"] = bare_multi

    advisory_lines: list[str] = []
    if notes:
        summary = " ".join(f"{name}={count}" for name, count in notes.items())
        advisory_lines.append(f"[advisory] {path.name}: {summary}")
    return advisory_lines, errors


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

    for message in _check_placeholders(path):
        errors += 1
        print(f"[FAIL] {message}")

    advisory_lines, hygiene_errors = _hygiene(path)
    for message in hygiene_errors:
        errors += 1
        print(f"[FAIL] {message}")
    for line in advisory_lines:
        print(line)

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
