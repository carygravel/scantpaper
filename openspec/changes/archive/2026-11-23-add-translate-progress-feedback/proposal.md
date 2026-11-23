# Proposal

## Why

A `translate` batch makes two to four model calls per entry and prints
nothing until the process exits. The French batch in this working tree took
1 h 34 m for 322 entries (3.4 entries/min, 17.6 s/entry) and reported only
at the end. The planned first run for every remaining language selects
10,289 entries, which is about 50 hours of wall clock and $18 of calls at
that rate, in batches long enough to cross a working day.

During such a run an operator cannot tell "running", "slow" and "hung"
apart, cannot answer whether the batch will finish before they leave, and
cannot see the run at all when it is started by an agent that only receives
a command's output when it exits. A second batch for another language may
be running at the same time, as the French one is now, which makes the
silence harder to interpret rather than easier.

## What Changes

- Print a start banner before the first model request: selected, skipped and
  unsupported counts, the spend estimate, and a duration estimate derived
  from the language's own `gate_runs` history.
- Print one timestamped line per entry to stderr with cost-weighted
  progress, observed rate, spend so far against `--max-cost`, a rounded
  ETA band and the expected local completion time.
- Add `--progress {auto,line,none}`. `auto` uses lines on a terminal and
  stays quiet when stderr is redirected, so an agent's captured output
  does not grow by one line per entry; a log file selects `line`
  explicitly. `--json` stdout stays exactly one document.
- Write a small per-language batch state file under `.cache/translate/`
  after every entry, atomically, recording pid, start, selection, done,
  approved, abstained, spend, progress weight, ETA, update time and any
  call that has run past a stall threshold.
- Add a read-only `status` command (`--json`, `--language`) that reports
  every language that has a live batch state or recent ledger activity,
  including a second language running in parallel. It reads local files
  only and needs no model credential.
- Add `--max-time` so a run stops between entries at a deadline and reports
  through the existing `stopped` channel. This lets a caller that cannot
  watch a stream run bounded slices whose exit report is the progress
  signal.
- Treat Ctrl-C as a clean stop: report entries done, entries left and spend,
  and print the exact command that resumes the batch. Every approval is
  already persisted per entry, so a rerun skips it.
- Document the operator and agent recipes in `po/README.md`.

Deliberately out of scope: changing how calls are scheduled. Measured role
latencies (proposer median 2.4 s, judge median 7.7 s but mean 16.0 s) make
throughput a larger change with a different risk profile, so it gets its
own proposal. It does not change the total cost either.

## Capabilities

### New Capabilities

None: the behaviour belongs to the existing gate and its batch commands.

### Modified Capabilities

- `machine-translation-gate`: add requirements for batch observability —
  a start banner, per-entry progress with a bounded completion estimate, a
  machine-readable batch state, a credential-free `status`, a wall-clock
  budget, and an interrupted run that reports and names its resume command.

## Impact

- `dev/translation_gate.py`: a reporter and clock seam in `_run_batch`,
  batch state writing, the `status` subcommand, `--progress`, `--max-time`
  and interrupt handling; `BatchReport` gains elapsed time and throughput.
- `dev/tests/test_translation_gate.py`: an injected clock, formatting and
  estimate tests, `status` tests, the `--max-time` stop and Ctrl-C.
- `po/README.md`: the "Translating missing entries" section gains the
  progress, status and bounded-run workflow, plus one agent recipe.
- `.cache/translate/*.json` (new, one file per running language);
  `.cache/` is already ignored by Git.
- No new dependency, no catalog or ledger schema change, and no change to
  the number of model calls or their cost.
