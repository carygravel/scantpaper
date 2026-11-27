# Proposal

## Why

A completed OpenSpec change can ship without ever being archived, and nothing
notices. Five changes are in that state right now: their code shipped between
4.0.3 and 4.0.4, their tasks are all ticked, and their deltas have never
reached `openspec/specs/`. The spec tree is therefore missing 12 requirements
and 41 scenarios of already-shipped behaviour, including a whole capability
(`openspec-cli-version`) whose specification has never existed.

The same defect has a second face. `openspec archive` applies a delta to the
main specs without validating the result, so archiving a requirement that has
grown past OpenSpec's 500-character limit succeeds and then fails the very
next CI step, `openspec validate --specs --strict`. The safe-looking option is
therefore to not archive, which leaves CI green and the spec stale. That is
how the backlog formed: 22 archived deltas already exceed 500 characters
while every requirement in `openspec/specs/` is at or below it, because the
main specs are trimmed by hand in periodic `:rotating_light:` cleanup
commits rather than at archive time.

Both faces have the same root cause: CI validates the main specs and the
archive, but never the active changes, and never whether a change should
still be active. Fixing the spec text is not enough; the gap that let it drift
has to close.

## What Changes

- **Clear the backlog.** Archive `watch-openspec-releases`,
  `fix-manual-word-inside-ocr-para-lost-on-save`,
  `restore-bilevel-g4-after-pdfa`, `preserve-ligature-text-mapping` and
  `honor-cancel-through-pdf-save`, in an order that respects the two that
  share `save-searchable-text-layer`. Three of them need the same treatment
  recently applied to the lineart fix: split
  the accreting requirement into requirements that each state one behaviour,
  so the merged text stays under the 500-character limit.
- **Validate every active change.** Add
  `openspec validate --changes --strict --no-interactive` as a CI step,
  alongside the existing `--specs` and `--archived` steps. It reports the
  over-long delta at authoring time instead of after the archive has already
  landed it.
- **Fail on a completed change that is still active.** `openspec list --json`
  reports `status: complete` only when every task is ticked, so a complete
  change means "ready to archive". CI SHALL fail when one is still under
  `openspec/changes/`, with one entry listing the offending names.
- **Document the gate.** Add the two checks and the "archive in the same
  commit" rule to `AGENTS.md`, where the OpenSpec workflow is already
  described.

No escape hatch is introduced. A deliberately deferred task is already
rewritten as prose naming its tracking issue, so "complete" stays a truthful
signal; a change that is complete but held for review can stay uncommitted,
which is where the current five should have stayed.

## Capabilities

### New Capabilities

- `change-lifecycle`: keeps the OpenSpec change tree valid and current - every
  active change is strict-valid, a change whose tasks are all ticked is
  archived rather than left active, and archiving leaves the main specs
  strict-valid.

### Modified Capabilities

(none)

## Impact

- `.github/workflows/test.yml`: the new `--changes` step and the archival gate
  in the three jobs that install OpenSpec.
- `dev/check_openspec.py` and `dev/tests/test_openspec.py`: the recorded
  validation command list the scheduled version check replays and asserts
  against the workflow.
- A new developer check for the archival gate, under `dev/` with tests beside
  it in `dev/tests/`, following the existing script layout.
- `AGENTS.md`: the two new gates and the archive-in-the-same-commit rule.
- Five change directories move to `openspec/changes/archive/`, creating
  `openspec/specs/openspec-cli-version/` and rewriting requirements in
  `openspec/specs/pdf-image-compression/`,
  `openspec/specs/background-job-cancellation/` and
  `openspec/specs/save-searchable-text-layer/`.
- No application code, dependency, data-model or user-visible behaviour
  change, so no `README.md` or `changelog.md` entry; the collaboration guide
  is the user-facing document here.
