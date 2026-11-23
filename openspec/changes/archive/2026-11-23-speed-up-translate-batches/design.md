# Design

## Context

See `proposal.md` — Why. The relevant mechanics:

- `_run_batch()` (`dev/translation_gate.py`) is a strictly sequential loop.
  Per entry it calls `run_gate`/`run_plural_gate`, which make two proposer
  calls (`propose`/`propose_plural` loop over `config.proposers` one at a
  time), optionally a blind-judge call, and optionally a back-translation
  call.
- The batch wraps the model client once in `ObservedClient(run.client,
  reporter)`, which already classifies each prompt's role (`_classify_role`:
  proposer/judge/backtranslation) for the progress reporter.
- Every gate run is persisted per entry, so an abstained entry is safe to
  retry by a later batch; `--max-time`, resume and `status` already make
  partial runs observable (the progress change).
- The judge connects through the model client's single transport `--timeout`
  (default 60 s). `ModelError` from any call propagates out of `_run_batch`
  and aborts the whole batch. `CredentialError` is a sibling class of
  `GateError`, distinct from `ModelError`.
- `BatchRun` and `BatchReport` are frozen dataclasses; `_command_translate`
  builds both. The two unit-testable seams are the `ModelClient` Protocol and
  the `ObservedClient` wrapper.

Measured on the committed ledgers and the evidence store (2026-11-23): whole-
gate latency median 9.7 s / mean 15.3 s / p90 28.3 s across 2,818 runs;
proposer median 2.4 s (n=5080), back-translation median 4.7 s (n=1498), judge
median 7.7 s / mean 16.0 s / p90 29.7 s (n=1343). The judge's p90 is 30 s of
its 60 s transport allowance, and whole-gate runs reach 277 s.

## Goals / Non-Goals

**Goals:**

- A `translate` batch finishes sooner, measurably (entries/hour already
  reported), without changing any approval decision or its evidence.
- The slow/failed judge is a deferral, never a stall or an abort.
- Deterministic tests: no real sleeping, no dependence on wall-clock timing.

**Non-Goals:**

- Whole-batch pipelining (overlapping the next entry's proposers under the
  current judge call); see Open Questions.
- Changing the number or kind of judge calls, or the evidence they produce.
- Reducing total cost; cost per approved string is unchanged.
- A per-entry budget that aborts an in-flight request. `--max-time` and
  `--max-cost` already stop only between entries, and this change keeps that.

## Decisions

### D1. Proposer concurrency is a stdlib thread pool, order-preserving

`propose`/`propose_plural` build the per-deployment completions and run them
through a `concurrent.futures.ThreadPoolExecutor`, collecting by
`executor.map` (which preserves input order) over `config.proposers`. The
returned proposal list, the `_independent_families` check and the `calls`
evidence are therefore byte-identical to a serial run: only the scheduling
changes. `OpenAICompatibleClient.complete` is stateless per call (the payload,
connection and timer are all local), so it is safe under two threads.

The executor is created behind a small module-level factory
(`_concurrent_map(worker, items, max_workers)`), so a test can swap it for a
synchronous inline runner or assert the overlap. On exit the pool waits for
started workers (`ThreadPoolExecutor` context manager), so the batch does not
leave a dangling request behind.

Failure semantics are unchanged: the first exception from a proposer
propagates and aborts the batch, as one does today. Concurrency does not make
a failing proposer quieter.

The progress reporter's in-flight `waiting` field is advisory, but two
proposer threads can now write it concurrently; `begin_call`/`end_call` guard
it with a lock so the state file never holds a torn value.

### D2. The judge deadline is a per-role transport timeout at the batch seam

The batch already funnels every call through `ObservedClient`. Extend it with
`judge_timeout` and have `complete` forward `timeout=judge_timeout` to the
underlying model client only when `_classify_role(prompt) == "judge"`.
`ModelClient.complete` gains an optional `timeout` override and
`OpenAICompatibleClient.complete` uses it for that call's connection, so a
judge's socket dies at the deadline (`socket.timeout` -> `ModelError`) while
every other role keeps the transport `--timeout`.

This keeps `blind_judge`'s signature and prompt logic untouched (the project's
`PLR0913` cap rules out growing its argument list) and concentrates the
scheduling policy in the one place the batch already controls. `--judge-timeout`
(default `DEFAULT_JUDGE_TIMEOUT_SECONDS = 20.0`, `0` disables) flows
`_command_translate` -> `BatchRun.judge_timeout` -> `ObservedClient`.

With the default 20 s, the deployment deadline and the measured judge p90 of
29.7 s, the cap defers roughly the slowest fifth of judge calls while leaving
the median 7.7 s and 80% of the tail untouched. Operators who prefer fewer
deferrals can raise it or disable it; the spec fixes only that the deadline
exists and is configurable.

### D3. Judge transport failure is an abstention, never an abort

`blind_judge`/`blind_judge_plural` catch `ModelError` around
`client.complete(judge, prompt)` and return `(None, "TIMEOUT", None)`. The
existing `index is None` branch in `run_gate`/`run_plural_gate` already
produces an unapproved `GateDecision` with reason "judge abstained or returned
no usable choice"; `_run_batch` records it as an abstained entry that stays
fuzzy and is retried later. When the verdict is `"TIMEOUT"`, the decision
reason becomes "judge timed out" so the abstention is distinguishable.

Only `ModelError` is caught. `CredentialError` (a missing key) is a sibling
class and keeps propagating as a hard error, satisfying the "credential is
still a hard error" requirement. As a side effect the direct `gate` command is
also hardened: a judge that fails no longer aborts the command.

### D4. The report names judge-timeout abstentions

`BatchReport` gains `judge_abstained: int`. `_run_batch` counts the abstained
decisions whose reason is "judge timed out". `_print_batch` prints
`judge timeout abstained N` only when `N > 0`, and `as_dict()` adds
`"judge_abstained": N` to the JSON report. The existing approved/abstained and
`status` numbers are unchanged.

## Risks / Trade-offs

- **More abstentions for the slowest judges** -> deferred entries are retried
  by a later batch (existing mechanism), and the default is a tunable that the
  operator can raise or disable; the report makes the deferral count visible.
- **Threads in the model path** -> the client is stateless per call, writes to
  the ledger/catalog stay on the main thread, and the reporter's in-flight
  field is locked; the interleaving of two proposer `begin_call`/`end_call`
  pairs is advisory-only.
- **One proposer fails under concurrency** -> the first exception aborts the
  batch exactly as today; concurrency never hides a failure.
- **A judge deadline could be reached on a healthy but slow provider** -> the
  verdict is an abstention, never an approval; a later batch retries, and the
  `--max-time`/resume flow already tolerates partial runs.
- **Timeouts are transport sockets, not an injected-clock cap** -> tests
  simulate the deadline with a fake client that raises `ModelError`, so they
  stay deterministic without sleeping.

## Migration Plan

Additive with one default change: before this change a judge call could run to
the 60 s transport timeout and, on failure, abort the batch; after it, the
judge has a 20 s deadline and failure becomes an abstention. Rollback is
`--judge-timeout 0` or removing the change. No ledger, catalog or config-file
schema change; `po/README.md` gains the `--judge-timeout` note and
`changelog.md` the user-visible line; no packaging change.

## Open Questions

- Whether the next throughput step should pipeline the following entry's
  proposers under the current judge call. It is strictly more complex (two
  entries' requests in flight, richer reporter bookkeeping) and changes
  nothing in this design.
