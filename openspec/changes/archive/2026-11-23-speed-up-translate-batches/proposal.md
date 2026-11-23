# Proposal

## Why

A `translate` batch's wall clock is dominated by the judge. Across the 2,818
recoverable gate runs the whole-gate latency is median 9.7 s, mean 15.3 s and
p90 28.3 s; the per-role breakdown from the evidence store is proposer median
2.4 s, back-translation median 4.7 s, and judge median 7.7 s but mean 16.0 s
with p90 29.7 s (1,343 judge calls). The judge's mean is more than twice its
median, so it is a long right tail, not steady work, that costs the wall
clock. The first run for every remaining language selects 10,289 entries,
about 50 serial hours at the observed rate.

Two wastes are cheap to remove without touching a single decision:

1. The two proposer calls for one entry run strictly serial. They are
   independent requests of 2.4-4.9 s each, so one full proposer latency is
   pure overhead on every judged entry.
2. A judge that is slow or fails mid-request stalls the whole batch. The model
   client applies one 60 s transport timeout to every call, and a `ModelError`
   from any call currently aborts the entire batch, not just the entry. Whole-
   gate runs reach 277 s; the worst entries are not slow, they are stuck.

## What Changes

- Run one entry's independent proposer calls concurrently instead of serially,
  keeping the same two proposals, the same order and the same recorded
  evidence. No decision, cost or call record changes.
- Give the judge call a dedicated, shorter deadline under `translate`, tuned
  with `--judge-timeout` (a documented default; `0` disables it and falls back
  to the transport timeout). A judge that does not answer within the deadline
  - or whose transport request fails - is recorded as an abstention with a
  clear reason and the batch continues, instead of stalling or aborting the
  run. The entry stays fuzzy and is retried by a later batch, exactly like any
  other abstention.
- Report how many entries ended this way, as a `judge_timeout` count in the
  JSON report and a line in the human report, so the operator can see when the
  bound defers entries rather than abandoning them.
- A missing credential is still a hard error. Only the model-transport failure
  class is downgraded to an abstention, never a missing key.

Deliberately out of scope: whole-batch pipelining (overlapping the next
entry's proposers under the current judge call), changing the number or kind
of judge calls, and any change to total cost. Every entry whose judge answers
within the deadline is decided exactly as it is today, with the same evidence.

## Capabilities

### New Capabilities

None: the behaviour belongs to the existing gate and its `translate` command.

### Modified Capabilities

- `machine-translation-gate`: add requirements that a batch runs one entry's
  independent proposer calls concurrently, bounds the judge call, and records
  a judge that exceeds its deadline or fails at the transport layer as an
  abstention rather than stalling or aborting the run.

## Impact

- `dev/translation_gate.py`: concurrent `propose`/`propose_plural`, a judge
  deadline on the batch (`BatchRun.judge_timeout`, `--judge-timeout`,
  `ObservedClient` forwarding a per-role timeout), `ModelError`-to-abstention
  in `blind_judge`/`blind_judge_plural`, and a `judge_timeout` count on
  `BatchReport`.
- `dev/tests/test_translation_gate.py`: concurrency (same proposals and order,
  proven overlap), judge-deadline abstention, credential-still-hard-error,
  decision-unchanged-within-budget, and the new report count.
- `po/README.md`: a short `--judge-timeout` note in the translate workflow.
- `changelog.md`: one user-visible line.
- No new dependency (stdlib `concurrent.futures`), no ledger or catalog schema
  change, and no change to the cost per approved string.
