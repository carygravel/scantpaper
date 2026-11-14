# Design

## Context

`dev/merge_po.py` owns the catalog refresh. Its `main()` currently regenerates
the template into `po/scantpaper/scantpaper.pot` (or uses `--pot`), globs
`src/*.po`, and runs `merge_catalog()` on every file.

`merge_catalog()` restores header dates and the original fuzzy flags, records
`#| msgid` predecessors, and writes a catalog only when its text changes. The
per-catalog work has no cross-catalog state; the template is the only shared
input. See `proposal.md` for the motivation.

## Goals / Non-Goals

**Goals:**

- Refresh named catalogs without changing the others.
- Preserve the default, release-time full refresh.
- Reject an invalid selection before writing the template or a catalog.
- Produce the same bytes for a catalog whether it is merged alone or with all
  catalogs.

**Non-Goals:**

- Enforce coverage, fail on missing entries, or clean up the existing backlog.
- Change the release procedure or translate any string.
- Change `msgmerge` flags or any per-catalog merge semantics.
- Add a `--dry-run` mode; the command is deterministic and already reports
  selection and changes.

## Decisions

### Repeatable `--language`, not `--catalog`

Add `--language` with `action="append"` and an empty default. An empty
selection means all catalogs, which keeps every existing invocation, including
`release_procedure.md`, unchanged. Each value is the catalog stem exactly as
written (`de`, `en_GB`), with no case folding or hyphen rewriting.

This matches the existing per-language tools (`audit_human_core.py`,
`translation_gate.py`, `rosetta_import.py`) and keeps one vocabulary across the
workflow.

Alternatives considered:

- `--catalog PATH`, repeatable. More general, but permits arbitrary paths and
  turns a language typo into a path typo; rejected.
- A comma-separated `--languages de,es`. One flag is compact, but it adds a
  second list syntax to a codebase that already uses repeatable options;
  rejected.
- Positional catalog files. Same path-typo problem as `--catalog`; rejected.

### Validate the selection before any write

Introduce `select_catalogs(src, languages)`, which maps stems to `src/*.po`
files, deduplicates and sorts the selection, and raises `MergeError` naming the
unknown values and the available languages. `main()` calls it before
`generate_template()` and `write_template()`, so `--language dee` leaves both
the template and the catalogs untouched. This is a deliberate reordering: the
current `main()` writes the template before it knows whether the merge inputs
are valid.

The error goes through the existing `MergeError` path, keeping the established
`error: ...` output and non-zero exit.

### Keep refreshing the template

A scoped run still regenerates and writes the template unless `--pot` is
given. `translation_gate.py`, `rosetta_import.py` and the catalog checks read
that file, and a stale template would make the next command act on an old
message set. It is gitignored, so the extra write creates no repository diff.

Alternative considered: write the template only for an unscoped merge. Rejected
because a scoped merge followed by `translation_gate.py translate` would use a
stale msgid set.

### Keep `merge_catalog()` semantics unchanged

Selection happens before the per-catalog loop. `merge_catalog()` keeps its
review-state restoration and predecessor recording, and the loop remains
independent per file. That independence is what makes the scoped result equal
to the full result; there is no ordering constraint to document or test beyond
the comparison.

One implementation detail changes to keep the documented second-run guarantee
true: GNU `msgmerge` drops `#|` from a non-fuzzy entry on a later run, so
`_record_predecessors()` restores the original entry's predecessor fields when
its key is unchanged. Without that, a changed msgid would be rewritten on
every merge and a scoped refresh would not be a no-op.

Keep `merge_catalogs(src, pot, languages=())` as the convenience entry point
for callers and tests. `main()` uses the path list returned by
`select_catalogs()` so the validation happens before the template write.

### Report selection and changes

Print both counts, for example:

```text
2 of 4 selected catalog(s) changed: de, es
```

This makes a filtered no-op visible and confirms that the filter matched
something. No repository script parses the current message, so changing it is
safe; the human-facing log is the only consumer.

### Documentation

Add a scoped example to the "Refresh the catalogs" section of `po/README.md`,
and state that the release procedure keeps the unscoped refresh. Correct the
current sentence that says a merge seeds new strings as `#, fuzzy`: `msgmerge`
adds them with an empty `msgstr` and no fuzzy flag.

## Risks / Trade-offs

- Partial merges can normalise drift -> the release procedure still runs the
  unscoped merge, and `summarise_po.py` already reports missing and stale
  counts per language. A separate change can add enforcement.
- Catalogs may sit at different template versions -> coverage is measured
  against the current template, so the difference is visible rather than
  hidden.
- A scoped run still updates the gitignored template -> documented in the
  README; it produces no repository diff.
- Changing the summary line could surprise a log reader -> both counts are
  printed and no automation parses it.

## Migration Plan

No data or configuration migration. The option is additive, and existing
commands behave exactly as before. Roll back by deleting the option, its tests
and the README paragraph; no catalog or ledger data depends on it.
