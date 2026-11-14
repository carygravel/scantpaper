# Proposal

## Why

`dev/merge_po.py` regenerates the template and merges all 44 catalogs in one
step. That is the right release-time behaviour, but it is a poor fit for
incremental translation: a template change of a few strings refreshes every
catalog and lets long-dormant backlogs dominate the diff. The branch rebase
that motivated this change added six msgids, but an unscoped merge would also
seed a 137-string backlog into the 40 catalogs that are not actively
maintained (about 5,600 new entries), hiding the six entries under noise.

Translation work is already scoped per language: `audit_human_core.py`,
`translation_gate.py` and `rosetta_import.py` all accept `--language`. The
merge is the only step that is all-or-nothing, so maintainers either point
`--src` at a temporary directory or run `msgmerge` by hand. Both bypass the
review-state guarantees the merge command owns.

## What Changes

- Add a repeatable `--language` option to `dev/merge_po.py`. Without it the
  command keeps today's behaviour and merges every catalog.
- Resolve each requested language to `po/scantpaper/<language>.po`. An unknown
  or misspelled name SHALL fail with a non-zero exit and name the available
  languages. Validation happens before the template or any catalog is written.
- Keep regenerating and writing the template. It is shared input for the gate,
  `rosetta_import.py` and `check_po.py`, and it is gitignored, so a partial
  merge adds no unrelated diff.
- Preserve the per-catalog merge contract unchanged: `--previous
  --no-fuzzy-matching`, keep existing fuzzy flags, record the previous msgid,
  preserve header dates, and make a second run a no-op.
- Report how many catalogs were selected and how many changed, so a filtered
  no-op is visible.
- Document the scoped invocation in `po/README.md` and correct the statement
  that new msgids are seeded fuzzy; `msgmerge` adds them untranslated.
- Keep `release_procedure.md` on the unscoped full merge, so a release still
  refreshes every catalog.

Out of scope: changing the release gate, enforcing a zero `missing` count in
CI, and clearing the existing backlog. Those are separate decisions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `translations`: the catalog-merge requirement changes from "update every
  catalog" to "update every catalog by default, or only the named languages".
  The determinism, previous-msgid and review-state guarantees stay the same,
  and a scoped merge MUST produce the same bytes for a catalog as the
  corresponding unscoped merge.

## Impact

- `dev/merge_po.py`: new option, language validation, filtered selection.
- `dev/tests/test_merge_po.py`: selection, unknown-language, default-all and
  idempotence coverage.
- `po/README.md`: scoped-merge example and accurate new-entry wording.
- No end-user behaviour, dependency, packaging or release-gate change.
- Partial refreshes leave catalogs at different template versions. The
  coverage report already measures each catalog against the current template,
  so the state stays visible per language.
