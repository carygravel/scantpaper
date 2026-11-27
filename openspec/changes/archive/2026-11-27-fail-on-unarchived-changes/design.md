# Design

## Context

See `proposal.md` - Why. The constraints that shape the approach:

- CI already validates `openspec/specs/` and `openspec/changes/archive/`, in
  three jobs that install the CLI from `dev/openspec-version`. Nothing
  validates `openspec/changes/`, and `openspec validate --changes --strict`
  is an existing CLI flag rather than something to write.
- `openspec list --json` already reports a per-change `status` of `no-tasks`,
  `in-progress` or `complete`, derived from the task checkboxes.
- `openspec archive` applies a delta without validating the result, so the
  "archived requirement is too long" failure surfaces one CI step later.
- Repository checks live under `dev/` with tests beside them in `dev/tests/`,
  and the validation commands CI runs are recorded once in
  `dev/check_openspec.py` (`DEFAULT_VALIDATE_COMMANDS`) and asserted against
  `test.yml` by `dev/tests/test_openspec.py`.
- Today `openspec validate --changes --strict` reports 4 passed, 4 failed:
  three shipped-but-unarchived deltas with over-long requirements, plus this
  change before its delta existed.

## Goals / Non-Goals

**Goals:**

- Fail a push that contains a strict-invalid active change, or a completed
  change that was never archived.
- Make the failure name every offending change, so the fix needs no further
  investigation.
- Keep the recorded command list single-sourced, so the scheduled CLI-version
  check exercises the same gates a push does.

**Non-Goals:**

- Changing how `openspec archive` validates, or wrapping it. The gate is the
  safety net, not a replacement for the tool.
- Repo-wide spec authorship rules beyond the length the validator already
  enforces.
- Enforcing archive directory naming or `.openspec.yaml` contents.

## Decisions

### D1 - Gate A is a workflow step, not a script

Add `openspec validate --changes --strict --no-interactive` next to the
existing `--specs` and `--archived` steps. The CLI implements the rule,
including the 500-character limit and the zero-delta check, so a local script
would only re-implement it and drift.

- Alternative: extend `dev/check_openspec.py`. Rejected - that script answers
  "is there a newer CLI release?", a scheduled question, not a per-push gate.

### D2 - Gate B is a small tested developer script

`dev/check_change_archive.py` runs `openspec list --json` and exits non-zero
naming every change with `status: complete`. It takes the CLI command as an
option so tests can point it at a stub, the way `dev/check_openspec.py` takes
a command name for `read_installed`.

- Alternative: a shell one-liner in `test.yml`. Rejected - it cannot be
  tested, and a multi-name failure message is the difference between a
  five-second fix and a debugging session.
- Alternative: a pytest test in `dev/tests/` that shells out to the real CLI.
  Rejected - the test suite runs in jobs that do not install OpenSpec, so the
  whole suite would gain an environment dependency it does not have today.
- Alternative: parse `tasks.md` checkboxes directly. Rejected - duplicates
  the upstream notion of `complete`, and would go wrong on the documented
  convention of rewriting a deferred task as prose.

### D3 - Completeness is read from the CLI, never inferred

`status` is the only input. `no-tasks` is deliberately not treated as
complete, so scaffolding a change and pushing it stays allowed; a change with
an unticked task stays allowed; only "every task ticked and still active"
fails. This keeps the gate aligned with `--archived`, which already requires
every archived task to be ticked.

### D4 - No allow-list, no hold marker

A change that is complete but held for review leaves its last task unticked
until the archive commit, which is the same edit either way. Introducing a
`hold:` marker would create a second way to be complete and an exemption that
nobody revisits - the failure mode being fixed.

### D5 - The backlog is split, not trimmed

Three deltas push a requirement past the limit. Each is split inside its own
change, before archiving, so the archive applies an already-valid delta and
the main spec never has to be trimmed afterwards:

- `restore-bilevel-g4-after-pdfa`: `Lossless page images survive PDF/A
  conversion` (847) keeps the lossless-in/lossless-out guarantee and its
  explicit request; **added** is restoring Group 4 after the converter
  rewrote a bilevel image, including images it inlined.
- `honor-cancel-through-pdf-save`: `Cancel stops running and queued jobs`
  (659) keeps queued/running work and progress teardown; **added** is
  stopping a PDF save in any phase, including after page assembly.
- `fix-manual-word-inside-ocr-para-lost-on-save`: `Saved PDF retains a
  searchable text layer` (573) keeps the structural guarantee and container
  levels, and the mixed-page scenario stays with it; **added** is a word
  inside a paragraph's box but outside its lines.

A MODIFIED block may not drop a scenario the current main spec already has, so
an existing scenario cannot be relocated into the added requirement - only the
delta's own new scenarios can move. The split therefore keeps every existing
scenario where it is and lets the added requirement carry the genuinely new
behaviour.

Scenarios move with the behaviour they assert; no scenario is dropped. Each
split is verified by comparing the scenario set before and after.

- Alternative: archive as-is and trim the main spec afterwards. Rejected -
  that is the loop that produced the 22 archived deltas whose text no longer
  matches `openspec/specs/`.

### D6 - Backfill order

`preserve-ligature-text-mapping` (adds a requirement) archives before
`fix-manual-word-inside-ocr-para-lost-on-save` (modifies two), so the split
is written against final text. `watch-openspec-releases` and
`honor-cancel-through-pdf-save` are independent and can land in any order.
`restore-bilevel-g4-after-pdfa` archives without waiting for the in-progress
`resample-bilevel-and-palette-pages`, whose delta only adds a requirement to
the same capability.

### D7 - Gate order and placement

Both new steps go immediately after `--archived`, in the three jobs that
already install the CLI: gate A first (a malformed delta is the cheaper
failure), then gate B. Gate B's command is recorded in
`DEFAULT_VALIDATE_COMMANDS`, so the scheduled CLI-version check replays it
against a candidate release before it is recommended.

## Risks / Trade-offs

- [A complete change held for review blocks the push] -> Leave the last task
  unticked until review finishes; `AGENTS.md` states this explicitly.
- [`openspec list --json` changes shape after a CLI bump] -> The scheduled
  `openspec-check` runs the recorded gates against the candidate, so a bump
  that breaks the parser is caught before it is adopted; the parser is covered
  by tests with a recorded fixture.
- [Splitting deltas rewrites committed artifacts] -> The code they describe
  has already shipped and the tests are the authority; only the delta text
  changes, and each split is reviewed by scenario set.
- [A split silently drops a scenario] -> Compare the scenario sets before and
  after each split, and let `--archived` require every task ticked.
- [The gate fires on work a contributor cannot fix without a CLI upgrade] ->
  The pin is shared and CI installs it, so an offline developer can run the
  same command; the failure message names the change to archive or split.

## Migration Plan

1. Split the three over-long deltas and confirm each change still validates
   on its own.
2. Archive all five changes and confirm `openspec validate --specs --strict`
   and `validate --archived` pass with the backlog gone.
3. Add gate A, gate B and its tests, record the command, update `AGENTS.md`,
   and push - CI is green at every step.
4. Rollback is deleting the two workflow steps and the script; the archives
   are additive and need no reversal.
