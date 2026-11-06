"""Build and query a cross-project translation-memory index.

The index is a local SQLite database (``.cache/translation-memory.sqlite3`` by
default), reproducible from installed ``.mo`` catalogs plus optional upstream
or Ubuntu language-pack trees. It is never committed; ``po/tm-sources.json``
is the committed licence and provenance manifest.

A source string is normalised by stripping gettext mnemonics, collapsing
whitespace, applying NFKD and case-folding. Dominance counts distinct source
*projects*, not raw occurrences, so one large catalog cannot outvote several
independent projects that agree.

A catalog is indexed only when the manifest names a licence for its project
and language and that licence is compatible with this GPL-3.0-only project.
The index is evidence for the gate; it never approves a string by itself.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import polib

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / ".cache" / "translation-memory.sqlite3"
DEFAULT_MANIFEST = REPO_ROOT / "po" / "tm-sources.json"
DEFAULT_LOCALE_ROOT = Path("/usr/share/locale")
MANIFEST_VERSION = 1
WILDCARD_LANGUAGE = "*"

# SPDX licences compatible with distributing the result under GPL-3.0-only.
_COMPATIBLE_LICENSES = frozenset(
    {
        "0BSD",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "GPL-2.0-or-later",
        "GPL-3.0-only",
        "GPL-3.0-or-later",
        "ISC",
        "LGPL-2.1-or-later",
        "LGPL-3.0-or-later",
        "MIT",
        "MPL-2.0",
    }
)


class TmError(Exception):
    """A manifest, corpus or database problem safe to show the user."""


@dataclass(frozen=True)
class ManifestEntry:
    """One licence and provenance rule in ``po/tm-sources.json``."""

    project: str
    language: str
    license: str
    origin: str


@dataclass(frozen=True)
class Source:
    """One catalog to index."""

    project: str
    language: str
    origin: str
    path: Path
    license: str


@dataclass(frozen=True)
class ImportOptions:
    """Explicit overrides for an imported upstream tree."""

    root: Path | None = None
    project: str | None = None
    language: str | None = None
    license: str | None = None


@dataclass
class BuildStats:
    """Counts from one index build."""

    sources: int = 0
    entries: int = 0
    skipped: list[str] = field(default_factory=list)
    projects: set[str] = field(default_factory=set)
    languages: set[str] = field(default_factory=set)


def normalize(text: str) -> str:
    """Normalise a msgid for cross-project matching."""
    stripped = text.replace("_", "").replace("&", "")
    collapsed = " ".join(stripped.split())
    return unicodedata.normalize("NFKD", collapsed).casefold()


def is_compatible(license_name: str) -> bool:
    """Return whether a licence may be used as evidence for GPL-3.0-only."""
    return license_name.strip() in _COMPATIBLE_LICENSES


def load_manifest(path: Path) -> list[ManifestEntry]:
    """Load the committed source manifest."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        msg = f"cannot read manifest {path}: {error}"
        raise TmError(msg) from error
    if not isinstance(data, dict) or data.get("version") != MANIFEST_VERSION:
        msg = f"{path} is not a version-{MANIFEST_VERSION} manifest"
        raise TmError(msg)
    sources = data.get("sources")
    if not isinstance(sources, list):
        msg = f"{path} has no 'sources' list"
        raise TmError(msg)

    entries: list[ManifestEntry] = []
    for source in sources:
        if not isinstance(source, dict):
            msg = f"{path} has a non-object source"
            raise TmError(msg)
        fields = [source.get(field) for field in ("project", "license", "origin")]
        if not all(isinstance(field, str) and field for field in fields):
            msg = f"{path} has a source without project, license and origin"
            raise TmError(msg)
        language = source.get("language", WILDCARD_LANGUAGE)
        if not isinstance(language, str) or not language:
            msg = f"{path} has a source without a language"
            raise TmError(msg)
        entries.append(
            ManifestEntry(
                project=fields[0],
                language=language,
                license=fields[1],
                origin=fields[2],
            )
        )
    return entries


def manifest_entry_for(
    manifest: Iterable[ManifestEntry],
    project: str,
    language: str,
) -> ManifestEntry | None:
    """Return the most specific manifest rule for a project and language."""
    wildcard: ManifestEntry | None = None
    for entry in manifest:
        if entry.project != project:
            continue
        if entry.language == language:
            return entry
        if entry.language == WILDCARD_LANGUAGE:
            wildcard = entry
    return wildcard


def iter_locale_catalogs(root: Path) -> Iterator[tuple[str, str, str, Path]]:
    """Yield (project, language, origin, path) for installed ``.mo`` catalogs."""
    if not root.is_dir():
        return
    for path in sorted(root.glob("*/LC_MESSAGES/*.mo")):
        language = path.parent.parent.name
        project = path.stem
        yield project, language, str(path), path


def iter_import_tree(
    root: Path,
    *,
    project: str | None,
    language: str | None,
) -> Iterator[tuple[str, str, str, Path]]:
    """Yield catalogs from an upstream or Ubuntu language-pack tree."""
    if not root.is_dir():
        msg = f"import tree {root} does not exist"
        raise TmError(msg)
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".po", ".mo"} or not path.is_file():
            continue
        if path.parent.name == "LC_MESSAGES":
            inferred_language = path.parent.parent.name
            inferred_project = path.stem
        else:
            inferred_language = language or path.stem
            inferred_project = project or path.parent.name
        if not inferred_project or not inferred_language:
            msg = f"cannot infer project and language for {path}"
            raise TmError(msg)
        yield inferred_project, inferred_language, str(path), path


def resolve_sources(
    manifest: list[ManifestEntry],
    *,
    locale_root: Path = DEFAULT_LOCALE_ROOT,
    options: ImportOptions | None = None,
) -> tuple[list[Source], list[str]]:
    """Resolve catalogs to index, returning accepted sources and skips."""
    options = options or ImportOptions()
    candidates: list[tuple[str, str, str, Path]] = []
    if options.root is not None:
        candidates.extend(
            iter_import_tree(
                options.root,
                project=options.project,
                language=options.language,
            )
        )
    else:
        candidates.extend(iter_locale_catalogs(locale_root))

    sources: list[Source] = []
    skipped: list[str] = []
    for candidate_project, candidate_language, origin, path in candidates:
        rule = manifest_entry_for(manifest, candidate_project, candidate_language)
        resolved_license = options.license or (rule.license if rule else None)
        if resolved_license is None:
            skipped.append(f"{path}: no licence in the manifest")
            continue
        if not is_compatible(resolved_license):
            skipped.append(f"{path}: incompatible licence {resolved_license}")
            continue
        sources.append(
            Source(
                project=candidate_project,
                language=candidate_language,
                origin=origin,
                path=path,
                license=resolved_license,
            )
        )
    return sources, skipped


def _connect(path: Path) -> sqlite3.Connection:
    """Open the index and create its schema."""
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY,
            project TEXT NOT NULL,
            language TEXT NOT NULL,
            license TEXT NOT NULL,
            origin TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            UNIQUE(project, language, origin)
        );
        CREATE TABLE IF NOT EXISTS entries (
            source_id INTEGER NOT NULL REFERENCES sources(id),
            language TEXT NOT NULL,
            source_norm TEXT NOT NULL,
            target TEXT NOT NULL,
            target_norm TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS entries_lookup
            ON entries(language, source_norm);
        """
    )
    connection.execute("DELETE FROM entries")
    connection.execute("DELETE FROM sources")
    return connection


def _translations(entry: polib.POEntry | polib.MOEntry) -> list[str]:
    """Return the non-empty translated forms of an entry."""
    if entry.msgid_plural:
        values = list((entry.msgstr_plural or {}).values())
    else:
        values = [entry.msgstr]
    return [value for value in values if value.strip()]


def build_index(
    db_path: Path,
    sources: list[Source],
    skipped: list[str],
) -> BuildStats:
    """Build the SQLite index from resolved sources."""
    stats = BuildStats(skipped=list(skipped))
    connection = _connect(db_path)
    imported_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        for source in sources:
            cursor = connection.execute(
                "INSERT INTO sources "
                "(project, language, license, origin, imported_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    source.project,
                    source.language,
                    source.license,
                    source.origin,
                    imported_at,
                ),
            )
            source_id = cursor.lastrowid
            po = (
                polib.mofile(str(source.path))
                if source.path.suffix == ".mo"
                else polib.pofile(str(source.path))
            )
            added = 0
            for entry in po:
                if entry.obsolete or not entry.msgid:
                    continue
                source_norm = normalize(entry.msgid)
                for target in _translations(entry):
                    connection.execute(
                        "INSERT INTO entries "
                        "(source_id, language, source_norm, target, target_norm) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            source_id,
                            source.language,
                            source_norm,
                            target,
                            normalize(target),
                        ),
                    )
                    added += 1
            stats.sources += 1
            stats.entries += added
            stats.projects.add(source.project)
            stats.languages.add(source.language)
        connection.commit()
    finally:
        connection.close()
    return stats


def exact_matches(
    db_path: Path,
    source: str,
    language: str,
) -> list[tuple[str, int]]:
    """Return (target, distinct project count) matches for a source string."""
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "SELECT e.target, COUNT(DISTINCT s.project) AS projects "
            "FROM entries e JOIN sources s ON s.id = e.source_id "
            "WHERE e.language = ? AND e.source_norm = ? "
            "GROUP BY e.target ORDER BY projects DESC, e.target",
            (language, normalize(source)),
        ).fetchall()
    finally:
        connection.close()
    return [(str(target), int(count)) for target, count in rows]


def dominant_match(
    db_path: Path,
    source: str,
    language: str,
    *,
    minimum_projects: int = 2,
) -> str | None:
    """Return the single dominant translation, or None when it is not clear.

    Dominance is over distinct projects. A tie between the two strongest
    targets, or a winner supported by fewer than ``minimum_projects``, is not
    dominant.
    """
    matches = exact_matches(db_path, source, language)
    if not matches:
        return None
    best_target, best_projects = matches[0]
    if best_projects < minimum_projects:
        return None
    if len(matches) > 1 and matches[1][1] == best_projects:
        return None
    return best_target


def database_stats(db_path: Path) -> dict[str, object]:
    """Return source, entry and per-project counts from an existing index."""
    if not db_path.exists():
        msg = f"index {db_path} does not exist; build it first"
        raise TmError(msg)
    connection = sqlite3.connect(db_path)
    try:
        sources = connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        entries = connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        rows = connection.execute(
            "SELECT s.project, s.language, COUNT(*) "
            "FROM entries e JOIN sources s ON s.id = e.source_id "
            "GROUP BY s.project, s.language "
            "ORDER BY s.project, s.language"
        ).fetchall()
    finally:
        connection.close()
    return {
        "sources": int(sources),
        "entries": int(entries),
        "by_project": [
            {"project": project, "language": language, "entries": count}
            for project, language, count in rows
        ],
    }


def _print_stats(payload: dict[str, object]) -> None:
    """Print the stats payload."""
    print(f"sources {payload['sources']}, entries {payload['entries']}")
    rows = payload["by_project"]
    if not isinstance(rows, list):
        return
    for row in rows:
        if isinstance(row, dict):
            print(f"{row['project']:<24} {row['language']:<8} {row['entries']:>8}")


def main(argv: Iterable[str] | None = None) -> int:
    """Run the translation-memory command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--locale-root",
        type=Path,
        default=DEFAULT_LOCALE_ROOT,
        help="Root of installed locale catalogs (default: /usr/share/locale)",
    )
    parser.add_argument(
        "--import",
        dest="import_root",
        type=Path,
        help="Import an upstream or Ubuntu language-pack tree instead of the "
        "installed catalogs",
    )
    parser.add_argument("--project", help="Project name for an imported tree")
    parser.add_argument("--language", help="Language for an imported tree")
    parser.add_argument("--license", dest="license_name", help="SPDX licence")
    parser.add_argument("--stats", action="store_true", help="Print index stats")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.stats:
            _print_stats(database_stats(args.db))
            return 0
        manifest = load_manifest(args.manifest)
        options = ImportOptions(
            root=args.import_root,
            project=args.project,
            language=args.language,
            license=args.license_name,
        )
        sources, skipped = resolve_sources(
            manifest,
            locale_root=args.locale_root,
            options=options,
        )
        stats = build_index(args.db, sources, skipped)
        _print_stats(
            {
                "sources": stats.sources,
                "entries": stats.entries,
                "by_project": [],
            }
        )
        if stats.skipped:
            reasons: dict[str, int] = {}
            for message in stats.skipped:
                reason = message.rsplit(": ", 1)[-1]
                reasons[reason] = reasons.get(reason, 0) + 1
            for reason, count in sorted(reasons.items()):
                print(f"skipped {count}: {reason}", file=sys.stderr)
    except TmError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
