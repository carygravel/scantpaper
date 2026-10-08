"""Deterministic checks for translation catalogs.

For every `po/scantpaper/*.po` this runs `msgfmt --check` (format-specifier
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
  message text that is not in Unicode NFC form;
* translation-authoring defects, reported as advisory per catalog: a `msgstr`
  copied verbatim from a *different* msgid (the bad-`msgmerge` signature),
  and sibling controls such as `Select Odd`/`Select Even` given one
  translation;
* source-side defects, reported once over the msgid set: untranslatable
  plural hacks (a hard failure) plus case-only duplicates, concatenation
  fragments, doubled spaces, GREEK SMALL LETTER MU, and over-long strings.

Advisories never affect the exit status: a release is not blocked by one.

The msgid set is generated on the fly by `dev/generate_pot.py` into a
temporary directory, so a stale `scantpaper.pot` cannot hide a new source
string from the source-side checks. Pass `--pot PATH` to use an existing
template instead, which is how the tests exercise those checks.

Exit status is non-zero if any hard check fails. Run in CI via
`src/scantpaper/tests/test_po_files.py`.
"""

from __future__ import annotations

import argparse
import os
import re
import string
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import polib

REPO_ROOT = Path(__file__).resolve().parents[1]
DEV_DIR = REPO_ROOT / "dev"

# The GtkBuilder ITS rules dev/generate_pot.py extracts .ui strings with. They
# are vendored under dev/ so the msgid set is the same on every machine; the
# advisory below compares them against whatever gettext installed locally.
ITS_RULE_NAMES = ("gtkbuilder.its", "gtkbuilder.loc")
_ITS_SEARCH_PATHS = [
    Path("/usr/share/gettext/its"),
    Path("/usr/local/share/gettext/its"),
    Path("/opt/homebrew/share/gettext/its"),
]

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
    "ab": 0,
    "af": 3,
    "ar": 3,
    "be": 7,
    "bg": 40,
    "ca": 56,
    "cs": 122,
    "da": 168,
    "de": 142,
    "el": 116,
    "en_GB": 137,
    "en_US": 4,
    "es": 130,
    "eu": 168,
    "fa": 4,
    "fi": 143,
    "fr": 106,
    "gl": 102,
    "gu": 49,
    "he": 27,
    "hi": 3,
    "hr": 30,
    "hu": 143,
    "id": 3,
    "it": 141,
    "ja": 96,
    "ko": 41,
    "nb": 63,
    "nl": 100,
    "oc": 6,
    "pl": 139,
    "pt": 35,
    "pt_BR": 73,
    "ro": 3,
    "ru": 143,
    "sk": 130,
    "sl": 63,
    "sr": 3,
    "sv": 76,
    "tr": 128,
    "uk": 143,
    "vi": 3,
    "zh_CN": 94,
    "zh_TW": 11,
}

# A printf conversion letter preceded by whitespace directly after a `%`.
# A single `%` followed by whitespace and one of these letters is the
# translation-time rewrap artifact this check targets.
_PRINTF_POISON = re.compile(r"%\s+[diouxXeEfgGaAcspn]")

# A word character immediately followed by a parenthesised bare plural suffix,
# as in `Open image file(s)`. Such a string is not a counted message, so it
# cannot be expressed with `ngettext()`, and no target language has a portable
# equivalent for the bare `(s)`. A parenthesised unit or gloss -- `(Mb)`,
# `(DCT)`, `(regular expression)` -- does not match and remains legal.
_PLURAL_HACK = re.compile(r"\w\((?:s|es)\)")

# A printf placeholder, used to decide whether a msgid ending in a colon is a
# self-contained sentence or a fragment meant to be concatenated with a value.
_PRINTF_PLACEHOLDER = re.compile(r"%[-+ #0-9.*]*[diouxXeEfgGaAcspn]")

# A msgid ending in a colon, with no trailing word after it, is intended to be
# followed by a runtime value or list. The fragment pins the sentence's word
# order to English, so a locale cannot place the value elsewhere.
_FRAGMENT_END = re.compile(r":\s*$")

# GREEK SMALL LETTER MU, which SI uses for the `micro` prefix but which many
# fonts render identically to MICRO SIGN. Reported, never failed: the tree uses
# the SI-correct codepoint and the choice is a matter of convention.
_GREEK_MU = "μ"

# Msgids longer than this are reported as a translation-effort warning.
LONG_MSGID_CHARS = 200

# Sibling msgids whose translations must differ. Two of these being given the
# same string is always a mistake, in any language, because they name
# different controls.
SIBLING_PAIRS: tuple[tuple[str, str], ...] = (
    ("Select Odd", "Select Even"),
    ("_Odd", "_Even"),
    ("Left", "Right"),
    ("Top", "Bottom"),
    ("Width", "Height"),
)

_FORMATTER = string.Formatter()


def language_from_filename(path: Path) -> str:
    """Infer the language code from a `<lang>.po` filename."""
    return path.stem


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


def _carries_placeholder(text: str) -> bool:
    """Return True if text interpolates a value, as printf or str.format."""
    if _PRINTF_PLACEHOLDER.search(text.replace("%%", "")):
        return True
    fields = _format_fields(text)
    return bool(fields)


def _normalise_variant(text: str) -> str:
    """Fold a string for comparing it against other msgids.

    Lowercasing and dropping `_` makes `_Ok` and `_OK` compare equal, which is
    what distinguishes a mistranslation from a plausible rendering of the same
    label.
    """
    return text.replace("_", "").lower()


def _pot_msgids(pot_path: Path) -> list[str]:
    """Return the active, non-header msgids of a message template."""
    return [
        entry.msgid
        for entry in polib.pofile(str(pot_path))
        if entry.msgid and not entry.obsolete
    ]


def _generate_msgids() -> list[str]:
    """Run the POT generator in a temporary directory and return its msgids.

    Generating on the fly keeps the msgid set authoritative: a stale template
    cannot hide a new source string from the source-side checks. The
    repository's own `scantpaper.pot` is left alone.
    """
    env = dict(os.environ)
    src = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        [src, *([env["PYTHONPATH"]] if env.get("PYTHONPATH") is not None else [])]
    )
    with tempfile.TemporaryDirectory() as tmp:
        pot_path = Path(tmp) / "scantpaper.pot"
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "dev" / "generate_pot.py"),
                "--output",
                str(pot_path),
            ],
            cwd=tmp,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            _clean_generator_temp_files()
            message = (
                "could not generate the message template with "
                f"dev/generate_pot.py; it needs xgettext and msgcat on PATH.\n"
                f"{result.stderr.rstrip()}"
            )
            raise RuntimeError(message)
        return _pot_msgids(pot_path)


def _clean_generator_temp_files() -> None:
    """Remove the scratch templates generate_pot.py leaves behind on failure."""
    for name in ("_py_tmp.pot", "_ui_tmp.pot"):
        stray = REPO_ROOT / "src" / "scantpaper" / name
        if stray.exists():
            stray.unlink()


def source_msgids(pot: Path | None = None) -> list[str]:
    """Return the source msgid set, generating the template unless overridden."""
    return _pot_msgids(pot) if pot is not None else _generate_msgids()


def _format_fields(text: str) -> list[str] | None:
    """Return the str.format field names, or None if the text is malformed."""
    try:
        return [field for _, field, _, _ in _FORMATTER.parse(text) if field is not None]
    except ValueError:
        return None


def _check_plural_hacks(msgids: list[str]) -> list[str]:
    """Return hard-error messages for untranslatable plural-hack msgids."""
    return [
        f"msgid {msgid!r} embeds a plural hack; use ngettext() for counted "
        f"text, or reword so no parenthesised plural is needed"
        for msgid in msgids
        if _PLURAL_HACK.search(msgid)
    ]


def _case_only_duplicate_groups(msgids: list[str]) -> list[list[str]]:
    """Return groups of msgids that differ only by letter case."""
    folded: dict[str, set[str]] = defaultdict(set)
    for msgid in msgids:
        folded[msgid.lower()].add(msgid)
    return [sorted(group) for group in folded.values() if len(group) > 1]


def _first_difference(vendored: Path, installed: Path) -> int:
    """Return the 1-based number of the first line where two files differ."""
    vendored_lines = vendored.read_text(encoding="utf-8").splitlines()
    installed_lines = installed.read_text(encoding="utf-8").splitlines()
    for number, (left, right) in enumerate(
        zip(vendored_lines, installed_lines, strict=False), start=1
    ):
        if left != right:
            return number
    return min(len(vendored_lines), len(installed_lines)) + 1


def _its_advisories(its_dir: Path | None = None) -> list[str]:
    """Compare the vendored ITS rules against the ones gettext installed.

    The rules are vendored so that the msgid set does not vary with the gettext
    version or install layout of the generating machine. The cost of that
    choice is a silent divergence if upstream changes them, so report it here.
    This is advisory: the vendored copy is the one in use, and a mismatch is
    not a defect in this tree.
    """
    search = [Path(its_dir)] if its_dir is not None else _ITS_SEARCH_PATHS
    result: list[str] = []
    for name in ITS_RULE_NAMES:
        vendored = DEV_DIR / name
        if not vendored.is_file():
            continue
        found = [d / name for d in search if (d / name).is_file()]
        if not found:
            result.append(
                f"[advisory] ITS rules: no installed copy of {name} was found "
                f"in {', '.join(str(d) for d in search)}, so the vendored "
                f"{vendored.name} was not compared against upstream"
            )
            continue
        for installed in found:
            if installed.read_bytes() == vendored.read_bytes():
                result.append(f"[advisory] ITS rules: {vendored} matches {installed}")
            else:
                line = _first_difference(vendored, installed)
                result.append(
                    f"[advisory] ITS rules: {vendored} differs from "
                    f"{installed} from line {line} on; see dev/its-rules.md"
                )
    return result


def _source_advisories(msgids: list[str]) -> list[str]:
    """Return advisory lines for defects in the source msgid set.

    Every condition here identifies a string for a human to reword; none can be
    corrected automatically, and none should fail the build.
    """
    lines: list[str] = [
        "[advisory] source: msgids differ only by case: "
        + ", ".join(repr(m) for m in group)
        for group in _case_only_duplicate_groups(msgids)
    ]
    lines.extend(
        f"[advisory] source: {msgid!r} is a concatenation fragment; "
        "pass the value in the same translatable string so the "
        "sentence order is not fixed to English"
        for msgid in msgids
        if _FRAGMENT_END.search(msgid) and not _carries_placeholder(msgid)
    )
    lines.extend(
        f"[advisory] source: {msgid!r} contains a doubled space"
        for msgid in msgids
        if "  " in msgid
    )
    lines.extend(
        f"[advisory] source: {msgid!r} uses GREEK SMALL LETTER MU; "
        "confirm MICRO SIGN (U+00B5) is not intended"
        for msgid in msgids
        if _GREEK_MU in msgid
    )
    lines.extend(
        f"[advisory] source: msgid is {len(msgid)} characters "
        f"(over {LONG_MSGID_CHARS}), a translation effort risk: {msgid!r}"
        for msgid in msgids
        if len(msgid) > LONG_MSGID_CHARS
    )
    return lines


def _catalog_advisories(po: polib.POFile, name: str) -> list[str]:
    """Return advisory lines for mistranslations in one parsed catalog."""
    active = _active_entries(po)
    lines: list[str] = []

    # (e) A msgstr copied verbatim from a different msgid, the signature of a
    # bad msgmerge fuzzy binding. A msgstr that folds to its *own* msgid is
    # suppressed: `_Ok` and `_OK` are both msgids, so translating one as the
    # other is a plausible rendering of the same label, not a mismatch.
    by_variant: dict[str, set[str]] = defaultdict(set)
    for entry in active:
        by_variant[_normalise_variant(entry.msgid)].add(entry.msgid)
    lines.extend(
        f"[advisory] {name}: {entry.msgid!r} is translated as {body!r}, "
        "which is a different msgid in this catalog"
        for entry in active
        for body in _translated_strings(entry)
        if (variant := _normalise_variant(body))
        and variant != _normalise_variant(entry.msgid)
        and by_variant.get(variant) is not None
    )

    # (f) Siblings naming different controls, given the same translation.
    for first, second in SIBLING_PAIRS:
        left, right = po.find(first), po.find(second)
        if left is None or right is None:
            continue
        lines.extend(
            f"[advisory] {name}: {first!r} and {second!r} share the "
            f"translation {body!r}, but they name different controls"
            for body in sorted(
                set(_translated_strings(left)) & set(_translated_strings(right))
            )
        )

    return lines


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
        if id_fields is not None:
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
        if (fields := _format_fields(entry.msgid)) is not None
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

    for line in _catalog_advisories(polib.pofile(str(path)), path.name):
        print(line)

    return errors


def main() -> int:
    """Run the application entry point."""
    parser = argparse.ArgumentParser(description="Check translation catalogs")
    parser.add_argument(
        "--src",
        default="po/scantpaper",
        help="Source dir of .po files (default: po/scantpaper)",
    )
    parser.add_argument(
        "--pot",
        type=Path,
        help="Check against this message template instead of generating one",
    )
    parser.add_argument(
        "--its-dir",
        type=Path,
        help="Search this directory for installed copies of the vendored ITS "
        "rules, instead of the standard gettext locations",
    )
    args = parser.parse_args()

    for line in _its_advisories(args.its_dir):
        print(line)

    try:
        msgids = source_msgids(args.pot)
    except RuntimeError as error:
        print(f"[FAIL] {error}")
        return 1

    src = Path(args.src)
    total_errors = 0
    checked = 0
    for po_path in sorted(src.glob("*.po")):
        checked += 1
        total_errors += check_catalog(po_path)

    # Source-wide conditions are properties of the msgid set, so they are
    # evaluated and reported once rather than once per catalog.
    plural_hack_errors = _check_plural_hacks(msgids)
    for message in plural_hack_errors:
        print(f"[FAIL] {message}")
    total_errors += len(plural_hack_errors)

    for line in _source_advisories(msgids):
        print(line)

    print(f"\nChecked {checked} catalogs, {total_errors} error(s).")
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
