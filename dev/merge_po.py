"""Merge every catalog with the current template deterministically.

The command regenerates ``scantpaper.pot`` (or accepts ``--pot``), runs
``msgmerge --previous --no-fuzzy-matching`` for each catalog, and then restores
the state that a review depends on:

* an existing entry keeps its original fuzzy flags, so a merge neither clears
  a proposal nor marks reviewed text fuzzy;
* a changed msgid keeps the ``#| msgid`` predecessor that ``--previous``
  records;
* a new msgid does not inherit a fuzzy match from another string, because
  ``--no-fuzzy-matching`` is always passed;
* the header dates are preserved, so a second run on unchanged inputs
  produces no diff.

The pre-2026 snapshot is a git commit, not a file in ``po/``; the merge never
touches git history or the approval ledger.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import polib
from generate_pot import generate_template

if TYPE_CHECKING:
    from collections.abc import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = REPO_ROOT / "po" / "scantpaper"
DEFAULT_POT = DEFAULT_SRC / "scantpaper.pot"
DATE_FIELDS = ("POT-Creation-Date", "PO-Revision-Date")


class MergeError(Exception):
    """A merge input or tool failure that can be reported to the user."""


def entry_key(entry: polib.POEntry) -> tuple[str, str, str]:
    """Return the source-side key of an entry."""
    return (entry.msgctxt or "", entry.msgid, entry.msgid_plural or "")


def parse_catalog(text: str) -> polib.POFile:
    """Parse catalog text without leaving a temporary file behind."""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".po", encoding="utf-8", delete=False
    ) as handle:
        handle.write(text)
        name = handle.name
    try:
        return polib.pofile(name)
    finally:
        Path(name).unlink()


def template_is_current(pot_path: Path, generated: str) -> bool:
    """Return whether the generated template has the same message set."""
    if not pot_path.exists():
        return False
    current = polib.pofile(str(pot_path))
    proposed = parse_catalog(generated)
    return {entry_key(entry) for entry in current if entry.msgid} == {
        entry_key(entry) for entry in proposed if entry.msgid
    }


def write_template(pot_path: Path, generated: str) -> bool:
    """Write the template when its message set changed; return whether it did."""
    if template_is_current(pot_path, generated):
        return False
    pot_path.parent.mkdir(parents=True, exist_ok=True)
    pot_path.write_text(generated, encoding="utf-8")
    return True


def _run_msgmerge(catalog: Path, pot: Path) -> None:
    """Run msgmerge in place, keeping the previous msgid and no fuzzy match."""
    result = subprocess.run(
        [
            "msgmerge",
            "--quiet",
            "--previous",
            "--no-fuzzy-matching",
            "--backup=none",
            "--update",
            str(catalog),
            str(pot),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"msgmerge failed for {catalog}: {result.stderr.strip()}"
        raise MergeError(msg)


def _restore_review_state(original: polib.POFile, merged: polib.POFile) -> None:
    """Restore header dates and the original fuzzy flags after a merge."""
    for field in DATE_FIELDS:
        if field in original.metadata:
            merged.metadata[field] = original.metadata[field]

    original_flags = {
        entry_key(entry): frozenset(entry.flags)
        for entry in original
        if not entry.obsolete and entry.msgid
    }
    for entry in merged:
        if entry.obsolete or not entry.msgid:
            continue
        flags = original_flags.get(entry_key(entry))
        if flags is not None:
            entry.flags = list(flags)


def _predecessor_for(
    entry: polib.POEntry,
    by_location: dict[tuple[str, str], list[polib.POEntry]],
    merged_keys: set[tuple[str, str, str]],
) -> polib.POEntry | None:
    """Return the single vanished entry at this entry's source location."""
    candidates: dict[tuple[str, str, str], polib.POEntry] = {}
    for location in entry.occurrences:
        for old in by_location.get(tuple(location), []):
            if entry_key(old) not in merged_keys:
                candidates[entry_key(old)] = old
    if len(candidates) != 1:
        return None
    return next(iter(candidates.values()))


def _record_predecessors(original: polib.POFile, merged: polib.POFile) -> None:
    """Record the previous msgid for a changed entry.

    GNU gettext writes ``#| msgid`` only when fuzzy matching is enabled, but
    this command passes ``--no-fuzzy-matching``. It therefore matches a
    vanished entry to a new untranslated entry at the same source location and
    records the predecessor itself. The old translation is deliberately not
    adopted; it remains an untranslated proposal.

    ``msgmerge`` drops ``#|`` from a non-fuzzy entry on a later run, so an
    unchanged entry's predecessor is first restored from the original catalog.
    Without that, a second merge would rewrite the catalog.
    """
    merged_keys = {
        entry_key(entry) for entry in merged if not entry.obsolete and entry.msgid
    }
    original_keys = {
        entry_key(entry): entry
        for entry in original
        if not entry.obsolete and entry.msgid
    }
    by_location: dict[tuple[str, str], list[polib.POEntry]] = {}
    for entry in original:
        if entry.obsolete or not entry.msgid:
            continue
        for location in entry.occurrences:
            by_location.setdefault(tuple(location), []).append(entry)

    for entry in merged:
        if entry.obsolete or not entry.msgid or entry.previous_msgid is not None:
            continue
        if entry.msgstr or entry.msgstr_plural:
            continue
        previous = original_keys.get(entry_key(entry))
        if previous is not None and previous.previous_msgid is not None:
            entry.previous_msgid = previous.previous_msgid
            entry.previous_msgctxt = previous.previous_msgctxt
            entry.previous_msgid_plural = previous.previous_msgid_plural
            continue
        old = _predecessor_for(entry, by_location, merged_keys)
        if old is None:
            continue
        entry.previous_msgid = old.msgid
        entry.previous_msgctxt = old.msgctxt or None
        entry.previous_msgid_plural = old.msgid_plural or None


def _save_if_changed(path: Path, merged: polib.POFile, previous: str) -> bool:
    """Save a catalog only when its text differs from ``previous``.

    The comparison is against the text at the start of the run, not the file
    ``msgmerge`` rewrites in place, so restoring a dropped ``#|`` comment does
    not count as a change on a repeated merge.
    """
    with tempfile.NamedTemporaryFile(
        "w", suffix=".po", encoding="utf-8", delete=False
    ) as handle:
        name = handle.name
    try:
        merged.save(name)
        proposed = Path(name).read_text(encoding="utf-8")
        if proposed == previous:
            # msgmerge rewrites the file in place, so undo any text it dropped
            # (such as a restored #| comment) before reporting no change.
            if path.read_text(encoding="utf-8") != previous:
                path.write_text(previous, encoding="utf-8")
            return False
        path.write_text(proposed, encoding="utf-8")
        return True
    finally:
        Path(name).unlink(missing_ok=True)


def merge_catalog(catalog: Path, pot: Path) -> bool:
    """Merge one catalog and return whether its text changed."""
    original = polib.pofile(str(catalog))
    previous = catalog.read_text(encoding="utf-8")
    _run_msgmerge(catalog, pot)
    merged = polib.pofile(str(catalog))
    _restore_review_state(original, merged)
    _record_predecessors(original, merged)
    return _save_if_changed(catalog, merged, previous)


def select_catalogs(src: Path, languages: Iterable[str] = ()) -> list[Path]:
    """Return the catalogs to merge, rejecting unknown language names."""
    catalogs = {path.stem: path for path in sorted(src.glob("*.po"))}
    requested = set(languages)
    if not requested:
        return list(catalogs.values())
    unknown = sorted(requested - catalogs.keys())
    if unknown:
        available = ", ".join(sorted(catalogs)) or "none"
        msg = f"unknown language(s): {', '.join(unknown)} (available: {available})"
        raise MergeError(msg)
    return [catalogs[language] for language in sorted(requested)]


def merge_catalogs(src: Path, pot: Path, languages: Iterable[str] = ()) -> list[str]:
    """Merge the selected catalogs in ``src``; return the changed languages."""
    selected = select_catalogs(src, languages)
    return [path.stem for path in selected if merge_catalog(path, pot)]


def main(argv: Iterable[str] | None = None) -> int:
    """Run the merge command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument(
        "--pot",
        type=Path,
        help="Use this template instead of regenerating scantpaper.pot",
    )
    parser.add_argument(
        "--language",
        action="append",
        default=[],
        help="Merge only this language catalog; repeat for several",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.src.is_dir():
        print(f"error: {args.src} does not exist", file=sys.stderr)
        return 1

    try:
        selected = select_catalogs(args.src, args.language)
        if args.pot is not None:
            pot = args.pot
        else:
            pot = DEFAULT_POT
            write_template(pot, generate_template())
        changed = [path.stem for path in selected if merge_catalog(path, pot)]
    except MergeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(
        f"{len(changed)} of {len(selected)} selected catalog(s) changed: "
        f"{', '.join(changed) or 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
