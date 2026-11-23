# Design

## Context

See `proposal.md` — Why. The relevant mechanics in `dev/translation_gate.py`:

- **Back-translation is the one unguarded judge call.** `blind_judge()`
  (line 1313) and `blind_judge_plural()` (line 1347) wrap their judge call in
  `try/except ModelError` and return `("TIMEOUT", None)`, which the caller
  turns into an abstention. `back_translation_preserves()` (line 1383) does
  not: a `ModelError` there propagates up through `run_gate`/`run_plural_gate`
  and out of the batch loop in `_run_batch` (`dev/translation_gate.py`), which
  has no per-entry `ModelError` handler; the outer `except (GateError, ...)`
  in `_command_translate` prints the error and exits 1. This is the exact
  failure observed live on the Danish catalog: a GLM read timeout on the
  back-translation leg killed a whole 30-minute slice, resumable only because
  every completed entry had already been persisted.
- **Back-translation never gets the judge deadline.** `_classify_role()`
  (line 1189) classifies the prompt as `"backtranslation"`, not `"judge"`, so
  `ObservedClient.complete()` applies `judge_timeout` only to blind-judge
  prompts. The judge tail is the wall-clock sink (design notes: judge mean
  16 s, back-translation mean 5.6 s), yet only the blind-judge leg is capped.
- **Qualification and drift are invisible.** `qualify_release()` (line 1877)
  and `drift_probe()` (line 2049) run plain sequential loops over
  `client.complete`, write no state file, and print one summary line at the
  end. `status` infers only from recent `gate_runs`; qualification/drift never
  write `gate_runs`, so a live run has zero observable signal from any
  channel.
- **Progress machinery is translate-shaped.** `ProgressReporter`
  (line 3586), the state-file path `.cache/translate/<lang>.json`
  (`STATE_DIR`, line 109), and `status`'s enumeration (`_status_languages`,
  line 4222) are all built for the batch loop's approved/abstained/weight
  model. The design for that change (D4) deliberately says "one file per
  language, so parallel batches never write the same path" — an assumption
  that holds only for one activity type, and breaks when three releases
  qualify in parallel.

## Goals / Non-Goals

**Goals:**

- A `ModelError` on the back-translation judge call abstains that one string
  with a distinct, reportable reason; the batch survives and the string is
  retried by a later batch. Same behaviour for singular and plural paths.
- `qualify` and `drift` report progress through the existing `status` channel:
  per-action state files that never collide, a live bare-score readout for
  qualification, and the waiting/stall signal.
- The abstention reason and the new status records are visible in the batch
  report / `status` output without changing the JSON contract of either where
  it would break existing consumers.

**Non-Goals:**

- Retrying the failed back-translation call in-process (option B) — see
  Decisions; the batch-level resume is the retry mechanism.
- Hardening the *proposer* legs against `ModelError` (option C) — deferred:
  out of scope for this change, recorded as a follow-up.
- Changing the judge deadline for back-translation prompts (option D) —
  deferred; noted because it clusters with the same call boundaries.
- `--progress`/`--max-time` parity on `qualify`/`drift` — qualification is
  already bounded by `--count` and writes an atomic ledger record, so a
  wall-clock budget buys little. This change delivers live, credential-free
  visibility, not wall-clock control.
- Any change to the ledger schema, evidence semantics, call scheduling or
  model choice.

## Decisions

### D1. Back-translation timeout becomes an abstention (option A)

`back_translation_preserves()` catches `ModelError` around its judge call and
returns a tri-state that the callers (`run_gate` at line 1547, `run_plural_gate`
at line 1714) map to an abstention with the distinct reason
`back-translation unavailable` — versus the existing
`back-translation changed the meaning` for a genuine mismatch, and
`judge timed out` for the blind judge. The failed call is not appended to
`calls` (it produced no completion), matching how `blind_judge` records a
timeout.

Why A over the alternatives, which are recorded for the record:

- **B — retry once in-process.** Read timeouts are often transient (the GLM
  call succeeded on the next slice), so a single retry would cut spurious
  full-entry re-runs. Rejected for this change: it adds a latency tail, a
  "when do we give up" policy, and a second guard on the same evidence leg;
  the batch-level resume already retries the entry safely. A good follow-up if
  the abstention rate proves noisy.
- **C — catch `ModelError` at the batch-entry boundary.** Fixes proposers
  too (a down proposer today also kills the batch). Rejected for this change:
  it changes budget semantics (a masked outage re-probes every entry) and
  needs a "skip this deployment for the rest of the batch" concept to be
  right. Deferred; the single call site is the minimal correct floor.
- **D — apply the judge deadline to back-translation prompts.** Genuinely
  useful — the judge tail is the wall-clock sink and currently only half is
  capped — but orthogonal to the abort bug. Deferred so the change stays
  focused on correctness; noted in Risks.

### D2. The batch report distinguishes the abstention reason

The report's `judge timeout abstained N (retried by a later batch)` line is
extended so `back-translation unavailable` is counted and named distinctly
from `judge timed out` and `back-translation changed the meaning`. The report
already reconciles abstained reasons (`_run_batch` computes `judge_abstained`
from the reason string); the same pattern extends without changing the JSON
shape expected by tests.

### D3. Qualification and drift write their own action-scoped state files

New directories beside `STATE_DIR`, keyed by the activity identity so parallel
actions on one language cannot collide:

```
.cache/translate/<language>.json                 (existing, untouched)
.cache/qualify/<release>.json + language field   (one file per release)
.cache/drift/<deployment>.json + language field  (one file per deployment)
```

The archived design's "one file per language" assumption is scoped to
translate; qualify is keyed per (release, language) and drift per (deployment,
language), in the same atomic, advisory `_load_state`/`os.replace` style. The
languages are read from the file body (as `_status_languages` already does for
translate), so `status` can report an arbitrary language filter.

Why a new directory per action instead of one shared `.cache/gate/`:
visibility and cleanup win — a stale file describes one activity, and the
existing "live state, then recent ledger inference" logic stays per directory.
Why not reuse `.cache/translate/<language>.json`: the live/batch inference in
`_live_record` assumes batch fields (`selection`, `approved`, `abstained`,
`weights`); qualification's active fact is `matches`/bare `score`, which the
translate renderer does not know.

### D4. `status` reports qualification and drift records

`_status_languages` and the renderer/JSON path gain awareness of the new
directories. Each record carries enough to be self-describing without new
top-level context:

- qualification: `done`, `total`, `matches`, bare `score`, `tolerance`,
  `spent`, `rate`, `eta`, `waiting`, `age` — plus
  `score = matches / done` as a live readout of "how far above tolerance are
  we" (the actual question an operator asks a 0.48/0.35 run *before* it
  finishes).
- drift: `done`, `total`, `matches`, bare `score`, `threshold`, same
  progress fields.

The waiting/stall logic (`begin_call`/`end_call` in `ProgressReporter`, lines
~3715) is the machinery that turns "240 s of silence" into
`waiting 42s on model`; qualification and drift wrap their `client.complete`
in `ObservedClient` so that signal exists for them too, without reusing the
batch's approved/abstained accounting.

### D5. ETA for a uniform loop is simpler than for a batch

Qualification and drift are one deployment, one call per item, no judge, no
weights — so the cost-weighted band the batch needs is overkill. A linear
`elapsed ÷ done × remaining` plus a windowed median of recent per-item
durations, rounded to the same band display, is honest. The state file carries
`rate_seconds_per_item` and the same `eta_low/high` fields so the existing
`status` renderer (`_print_status`, line 4397) draws the band unchanged.

## Risks / Trade-offs

- **[D1 shrinks approvals on a flaky judge]** A genuinely good translation
  whose back-translation leg times out becomes an abstention and is re-run, so
  a flaky judge inflates re-runs → Mitigation: this is exactly the contract
  the blind judge already keeps; the batch resume is the retry; the distinct
  reason makes the cost visible in the report so it can justify option B
  (in-process retry) later.
- **[D3 leaves stale state files]** A killed `qualify`/`drift` leaves a file
  that `status` would show as abandoned after the age window →
  Mitigation: reuse the existing `_pid_alive` + `STATUS_ABANDONED_AFTER_SECONDS`
  logic verbatim; stale files are advisory and never block a rerun.
- **[D4 extends `status` output]** Adding records could surprise a consumer
  that assumed exactly one record per language → Mitigation: JSON keeps the
  per-record shape; a language with a live qualify and an idle translate still
  reports its existing translate record; the working tree's own tests own the
  contract.
- **[Uncapped back-translation tail persists (option D deferred)]** The judge
  deadline still misses the back-translation leg, so that tail can still be
  long even though it now aborts nothing → Mitigation: recorded as a follow-up;
  this change's guarantee is "never aborts", not "never slow".

## Migration Plan

Additive: no flag changes meaning, no ledger/catalog schema change. New state
directories are created on first use; the existing translate path is
untouched. Rollback removes the new directories and the reason string handling;
the `status` enumeration degrades back to translate-only without error.
Documentation to `po/README.md`; `changelog.md` gets the user-visible line.

## Open Questions

None that change the approach — the recorded options (B, C, D) are additive
follow-ups and do not alter this change's specs or tasks.
