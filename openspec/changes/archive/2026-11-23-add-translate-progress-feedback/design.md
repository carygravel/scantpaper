# Design

## Context

See `proposal.md` — Why. The relevant mechanics:

- `_run_batch()` (`dev/translation_gate.py`) is a strictly sequential loop.
  Per entry it calls `run_gate`/`run_plural_gate`, which make two proposer
  calls, optionally a blind-judge call, and optionally a back-translation
  call. It then rewrites the language ledger and, on approval, saves the
  catalog. It prints nothing.
- Every gate run is persisted, so the run is already crash-safe and
  resumable; the missing piece is only *visibility*.
- `gate_runs` records carry `timestamp`, `call_count`, `latency_ms` and
  `total_cost_usd`, so per-language throughput history already exists.
- `estimate_gate()` already computes per-entry token and cost estimates for
  the whole selection before the first call; the batch budget depends on it.
- `ModelClient` is a Protocol and `_run_batch` receives a client instance,
  so call boundaries are an existing seam.
- `.cache/` is Git-ignored; `dev/` tooling is outside the shipped-package
  coverage gate, and its tests live in `dev/tests/`.

Measured on the French batch in this working tree (322 gate runs,
2026-11-23 08:40Z–10:14Z):

| measure | value |
| --- | --- |
| throughput | 3.4 entries/min, 17.6 s/entry (median gap 13 s) |
| calls per entry | 2 (27%), 3 (34%), 4 (39%) |
| median duration by call count | 4.0 s / 12.0 s / 21.0 s |
| median duration by cost quartile | 4.0 / 11.0 / 16.0 / 26.5 s |
| correlation duration vs cost | 0.65 |
| local overhead per entry | about 0.1 s |
| abstain rate | 3.4% |
| cost | $0.00176/entry |

Call latencies across the evidence store: proposer median 2.4 s (mean
3.1 s), back-translation median 4.7 s (mean 5.6 s), judge median 7.7 s
(mean 16.0 s). The judge tail is where the wall clock goes.

The queue implied by "first run for every language" is 10,289 selected
entries: about 50 hours serial, about $18.

## Goals / Non-Goals

**Goals:**

- One cheap, credential-free query answers "live, how far, how long" for
  any language, including a batch this process did not start.
- Progress is printable without ever touching stdout, so `--json` stays a
  single document.
- The estimate is measured from the run itself, so contention from a
  parallel language is absorbed rather than assumed away.
- All output is deterministic under a fake clock, so tests never sleep.

**Non-Goals:**

- Changing call scheduling or model choice; total calls and cost stay the
  same.
- Streaming progress into an agent harness. Nothing in the tool can reach
  a caller that only receives output at exit; see D1.
- A GUI, web page or notification channel.
- Persisting any new audit fact. The ledger keeps its current schema.

## Decisions

### D1. Progress is pulled from a state file, not pushed down a stream

An agent sees a command's output only when the command ends: a foreground
call that exceeds the tool timeout moves to the background, and a
background call returns immediately and notifies at completion. A three
hour batch would therefore deliver 500 progress lines to the agent *after*
it is over — the opposite of useful, and context bloat.

So the run writes a small state file, and both humans and agents read it
through `status`:

```
 translate (any language)            agent / operator
   │  after each entry                 │
   ├─▶ .cache/translate/<lang>.json ──▶│ translation_gate.py status --json
   │   (atomic, ~200 B)                │   ├─ live: state file
   │                                   │   └─ fallback: ledger inference
   └─▶ stderr lines (tty only)         └─▶ one compact line, or one object
```

Alternatives: a stderr stream only (invisible to an agent, noisy in a
captured log); NDJSON on a pipe (needs a consumer, and a log file *is* the
state); a babysitting subagent (it can only poll the same file, at the
cost of another context).

### D2. The state file is operational, per language, and replaced atomically

Path: `.cache/translate/<language>.json`. Fields: `pid`, `host`,
`started_at`, `updated_at`, `language`, `catalog`, `selection`, `done`,
`approved`, `abstained`, `spent_usd`, `weight_total`, `weight_done`,
`eta_seconds`, `rate_seconds_per_entry`, `waiting` `{role, deployment,
since}` and `stopped`.

Written to a sibling temp file and `os.replace`d, so a reader never sees a
partial document. One file per language, so parallel batches never write
the same path.

The ledger is not the place for this: it is the audit record, validated by
its own tests, and it has no concept of a batch start or selection. A
progress write into `approvals/<lang>.json` would also multiply the 800 KB
rewrite that already happens per entry. Progress is volatile cache and
lives with the rest of the cache.

### D3. `status` reads live state first, then the ledger

```
for each language with a state file or a gate_run in the last 24h:
    if state file exists and pid is alive:  exact numbers, source=live
    else:                                   last gate_run, rate, selection
                                            from the catalog, source=inferred
```

The ledger fallback matters twice: it covers a run started before this
change (the French one), and it keeps working after `.cache` is wiped.
`status` never needs a model credential, always exits 0, and accepts
`--language` and `--json`. Its object per language is the same shape for
both sources, with `source` and `updated_age_seconds` so a caller can tell
how fresh and how exact the numbers are. It also sums today's spend across
languages, because `--max-cost` caps one batch while the account sees the
sum of the parallel batches.

Liveness: `done` changed recently (within `max(60 s, 3 × recent median)`),
or the pid is alive. Otherwise report the age and `abandoned` rather than
pretending there is an ETA. A pid alone is not proof: record `host` and
`started_at` and report "unverified" where `/proc` is unavailable.

### D4. The estimate is cost-weighted, windowed, banded and rounded

Per-entry work is dominated by how many calls the entry needs and how long
the judge takes, so the existing per-entry estimate is a good weight:

- elapsed ÷ weight_done gives seconds-per-weight; remaining weight gives
  the ETA, using the median of the last 20 entries rather than the
  cumulative mean, so contention and the observed 40% slowdown within a
  batch are absorbed within minutes.
- Cold start uses the language's own `gate_runs[].latency_ms` (French:
  16.4 s mean + 1.2 s overhead = 17.6 s/entry, which matched the observed
  rate), falling back to the cross-language median, then to a documented
  constant.
- The band comes from the observed 10th–90th percentile of seconds per
  unit weight, and the output is rounded to five minutes and shown as a
  local clock time, e.g. `eta 1h 30m–1h 55m (13:40–14:05)`. Ledger
  timestamps are UTC; display converts with `astimezone()`.

Simulation over the French durations (300 shuffles of 150 entries, median
error on remaining time):

| after N entries | count-based | cost-weighted |
| --- | --- | --- |
| 1 | 42% | 33% |
| 3 | 30% | 19% |
| 5 | 27% | 17% |
| 10 | 22% | 13% |
| 20 | 20% | 13% |

The 13% floor is network jitter; that is why the display is a band and not
a promise. Alternatives: a static seconds-per-entry constant (wrong by 2×
when a second language runs), a token-throughput model (no better than the
cost weight, more machinery), a point estimate (false precision).

### D5. Progress goes to stderr; `auto` means "only on a terminal"

`--progress {auto,line,none}`, default `auto`: `line` when stderr is a
tty, `none` otherwise. `--json` never changes this, and stdout is never
used for progress. A log file is captured output, so such a run passes
`--progress line` explicitly; an agent leaves it at `auto` and polls
`status`.

The start banner is part of the progress stream: selected, skipped,
unsupported, spend estimate, duration estimate and the prior it used.
Without it, "started wrong" and "running" look identical.

### D6. `--max-time` is a deadline checked between entries

It mirrors `--max-cost` in the loop and reports through the existing
`stopped` field (`time`, alongside `budget`). It never aborts an in-flight
request: a killed call loses its spend record and muddies the ledger. A
caller that cannot watch a stream runs slices of, say, 20 minutes; each
exit report is then the progress event, and the next slice resumes from
the persisted ledger.

### D7. Ctrl-C reports and names the resume command

Catch `KeyboardInterrupt` at the CLI, print entries done, entries left,
spend and the exact rerun command, then exit 130. An interrupt during a
call simply loses that entry's work; nothing was written for it, so the
rerun retries it. No new persistence is needed for correctness.

### D8. Clock and formatting are injected and pure

The reporter takes a clock (`now()` for wall time in UTC, `monotonic()`
for elapsed) and a stream. Formatting is a pure function of its inputs, so
tests assert exact strings and ETA arithmetic with crafted durations. No
sleeping, no reliance on `capsys` plus real time.

### D9. A stall is visible without a timer thread

Before each model call the reporter rewrites the state file with
`waiting={role, deployment, since}`; after the call it clears it. No
background thread and no periodic write. `status` computes
`now - since` and reports "waiting 42 s on judge". With the 60 s request
timeout, any longer silence is a fact worth surfacing; a threshold of
twice the recent median call duration marks it as a stall.

## Risks / Trade-offs

- **Pid reuse or a stale file after SIGKILL** → record `host` and
  `started_at`, verify against `/proc` where available, report `abandoned`
  after a long silence, and never let the file block a rerun; it is
  advisory.
- **ETA underestimates when a parallel batch starts mid-run** → windowed
  median plus a band, and the banner says which prior it used.
- **Abstentions keep `remaining > 0` forever** (the French catalog has 4
  such entries, one an empty `%dMb free in %s.`) → show batch progress and
  catalog progress as separate numbers, and have the resume hint name how
  many entries will be retried.
- **Clock changes (NTP, DST)** → elapsed from `monotonic()`, absolute
  times stored in UTC, display adapted to the local zone.
- **Agent context bloat** → `auto` stays quiet without a tty; the final
  `BatchReport` is already compact; `status` is one small object.
- **Parallel append to the evidence store** is an existing behaviour, not
  introduced here; the state files are per language, so this change adds
  no shared writer.
- **One extra small write per entry** → 200 B against the existing 800 KB
  ledger rewrite; negligible and easily measured.

## Migration Plan

Additive only: no flag changes meaning, no ledger or catalog schema change,
and the default `auto` keeps non-tty output as it is today, so existing
tests and captured logs are unaffected. Rollback is removing the new
flags, subcommand and cache directory. Documentation goes to
`po/README.md`; `changelog.md` gets the user-visible line. No packaging
change.

## Open Questions

- Whether `status` should also print a suggested split of the remaining
  queue across N parallel workers. Deferrable; it changes no spec.
- Whether to add a periodic heartbeat ticker for very long entries once
  D9's call-boundary signal proves insufficient in practice.
