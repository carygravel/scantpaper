# Proposal

## Why

Two gaps in the machine translation gate surfaced while completing the Danish
catalog. First, a single slow model call on the back-translation judge leg
raises `ModelError`, which propagates out of the batch loop and aborts an
entire `translate` run — losing the remaining selection even though every
completed entry is safely persisted. Second, `qualify` and `drift` — the
short, blocking steps that gate every later batch — run silently: no state
file, no `status` line, no observable signal until the final one-line
verdict, so an operator cannot tell a live run from a dead one.

## What Changes

- **Back-translation judge failure becomes a per-string abstention.** The
  back-translation judge call in `back_translation_preserves` (singular and
  plural paths) SHALL catch `ModelError` and abstain that string with a
  distinct reason (`back-translation unavailable`), exactly as the blind
  judge already does — the batch continues, and the abstained string is
  retried by a later batch. In this change the guarantee covers the
  back-translation judge leg; hardening the proposer legs is recorded as a
  deferred option in the design.
- **The new abstention reason is reported distinctly.** The batch report
  counts `back-translation unavailable` separately from
  `back-translation changed the meaning` and from `judge timed out`, so an
  operator can distinguish an infra failure from a genuine mismatch.
- **Progress and ETA cover qualification and drift.** `qualify` and `drift`
  SHALL write per-(action, release/deployment, language) state files
  (reused, not parallel-clashing) and `status` SHALL report them live,
  including a running bare score against the tolerance for qualification.
  The waiting/stall signal applies to these actions too.
- No change to call scheduling, evidence semantics or the ledger schema.

## Capabilities

### New Capabilities

None — both behaviours belong to the existing machine-gate capability.

### Modified Capabilities

- `machine-translation-gate`: The "evidence is unavailable" abstention
  path SHALL cover the back-translation judge call; a model-call failure
  SHALL abstain one string and never abort a batch. Progress reporting and
  `status` coverage SHALL extend from `translate` batches to `qualify` and
  `drift`, with per-action state files and a live score for qualification.

## Impact

- `dev/translation_gate.py`: `back_translation_preserves` (singular +
  plural), `run_gate`/`run_plural_gate` abstention reasons, `_run_batch`
  report accounting, `qualify_release`, `drift_probe`, `ProgressReporter`
  generalisation, `status` enumeration and record shape, CLI parsers for
  `qualify`/`drift`.
- `dev/tests/test_translation_gate.py`: error-path, reporting-scope and
  state-file tests for both improvements.
- `po/README.md`: document the new abstention reason and the widened
  progress/status coverage; `changelog.md` gets the user-visible line.
