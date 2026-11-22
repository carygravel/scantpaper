"""Validate and merge a downloaded Rosetta or language-pack export.

Launchpad has no bulk export API: a maintainer downloads one `.po` per project
and language from a logged-in web request. This tool takes that file, or an
Ubuntu language-pack tree, and merges it without network access.

An export is rejected when it contains a message that is not in the current
template, which is the signature of a stale or mismatched catalog. A valid
export updates an existing entry, clears its fuzzy flag only when the export
itself is confirmed, and can add a template message the catalog is missing.
Header dates from the export are not copied, so the catalog stays reviewable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import polib

if TYPE_CHECKING:
    from collections.abc import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = REPO_ROOT / "po" / "scantpaper"
DEFAULT_POT = DEFAULT_SRC / "scantpaper.pot"
DEFAULT_DOMAIN = "scantpaper"


class RosettaImportError(Exception):
    """A downloaded export that cannot be merged safely."""


def entry_key(entry: polib.POEntry) -> tuple[str, str, str]:
    """Return the source-side key of an entry."""
    return (entry.msgctxt or "", entry.msgid, entry.msgid_plural or "")


def has_text(entry: polib.POEntry) -> bool:
    """Return whether an entry carries a usable translation."""
    if entry.msgid_plural:
        return any(value.strip() for value in (entry.msgstr_plural or {}).values())
    return bool(entry.msgstr.strip())


def template_keys(pot: Path) -> set[tuple[str, str, str]]:
    """Return the active message keys of the current template."""
    return {
        entry_key(entry)
        for entry in polib.pofile(str(pot))
        if not entry.obsolete and entry.msgid
    }


def validate_export(
    export: polib.POFile,
    keys: set[tuple[str, str, str]],
    source: str,
) -> list[str]:
    """Return every export message that is absent from the template."""
    return [
        f"{source}: {entry.msgid!r} is not in the current template"
        for entry in export
        if not entry.obsolete and entry.msgid and entry_key(entry) not in keys
    ]


def merge_entry(
    catalog: polib.POFile,
    exported: polib.POEntry,
) -> bool:
    """Merge one exported translation into the catalog; return whether it changed."""
    target = catalog.find(exported.msgid, msgctxt=exported.msgctxt or False)
    if target is None:
        target = polib.POEntry(
            msgid=exported.msgid,
            msgstr=exported.msgstr,
            msgid_plural=exported.msgid_plural,
            occurrences=exported.occurrences,
        )
        target.msgctxt = exported.msgctxt
        catalog.append(target)
        created = True
    else:
        created = False

    before = (target.msgstr, dict(target.msgstr_plural or {}), set(target.flags))
    target.msgstr = exported.msgstr
    target.msgstr_plural = dict(exported.msgstr_plural or {})
    if exported.msgid_plural:
        target.msgid_plural = exported.msgid_plural
    target.flags = [flag for flag in target.flags if flag != "fuzzy"]
    if "fuzzy" in exported.flags:
        target.flags.append("fuzzy")
    after = (target.msgstr, dict(target.msgstr_plural or {}), set(target.flags))
    return created or before != after


def merge_export(
    catalog: polib.POFile,
    export: polib.POFile,
) -> int:
    """Merge a valid export and return the number of changed entries."""
    changed = 0
    for entry in export:
        if entry.obsolete or not entry.msgid or not has_text(entry):
            continue
        if merge_entry(catalog, entry):
            changed += 1
    return changed


def discover_exports(root: Path, domain: str) -> list[tuple[str, Path]]:
    """Return (language, path) pairs from a file or language-pack tree."""
    if root.is_file():
        return [(root.stem, root)]
    if not root.is_dir():
        msg = f"{root} does not exist"
        raise RosettaImportError(msg)
    found: list[tuple[str, Path]] = []
    for path in sorted(root.rglob("*.po")):
        if path.parent.name == "LC_MESSAGES":
            if path.stem != domain:
                continue
            found.append((path.parent.parent.name, path))
        else:
            found.append((path.stem, path))
    return found


def import_export(
    export_path: Path,
    language: str,
    *,
    src: Path,
    keys: set[tuple[str, str, str]],
    apply: bool,
) -> int:
    """Validate and merge one export; return the number of changed entries."""
    export = polib.pofile(str(export_path))
    problems = validate_export(export, keys, str(export_path))
    if problems:
        raise RosettaImportError("\n".join(problems))

    catalog_path = src / f"{language}.po"
    if catalog_path.exists():
        catalog = polib.pofile(str(catalog_path))
    else:
        catalog = polib.POFile()
        catalog.metadata = dict(export.metadata)

    changed = merge_export(catalog, export)
    if apply and changed:
        catalog.save(str(catalog_path))
    print(f"{language}: {changed} entries merged from {export_path}")
    return changed


def _language_filter(
    args: argparse.Namespace, candidates: list[tuple[str, Path]]
) -> list[tuple[str, Path]]:
    """Apply an optional language filter to discovered exports."""
    if not args.language:
        return candidates
    return [item for item in candidates if item[0] == args.language]


def main(argv: Iterable[str] | None = None) -> int:
    """Run the import command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pot", type=Path, default=DEFAULT_POT)
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--import", dest="import_root", type=Path, required=True)
    parser.add_argument("--language", help="Only import this language")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the merged catalogs (default: dry run)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        keys = template_keys(args.pot)
        candidates = _language_filter(
            args, discover_exports(args.import_root, args.domain)
        )
    except (RosettaImportError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if not candidates:
        print(
            f"error: no .po exports found under {args.import_root}",
            file=sys.stderr,
        )
        return 1

    try:
        total = 0
        for language, path in candidates:
            total += import_export(
                path,
                language,
                src=args.src,
                keys=keys,
                apply=args.apply,
            )
    except (RosettaImportError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if not args.apply:
        print("dry run: pass --apply to write the catalogs")
    print(f"{total} entries changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
