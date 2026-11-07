# Design

## Context

See `proposal.md` - Why.

`dev/translation_gate.py` already contains the drift machinery:

- `DriftRequest(release, deployment_id, language, probe, budget_usd)`
- `drift_probe(config, request, client)` runs one translation prompt per probe
  item, scores exact normalized matches, compares the score with
  `thresholds.drift` (default 0.75), and returns the score, threshold, pause
  flag, calls and cost.
- `estimate_drift(config, request)` prices the run, and `ensure_budget()`
  refuses an over-budget action before any request.
- `record_drift_excursion(ledger, result, since=...)` appends a paused
  `drift_excursions` record without demoting approvals.
- `load_probe(path)` reads `po/drift-probe/<language>.json`; `build-probes`
  already regenerates those files.

The CLI has `estimate --action drift` and `build-probes`, but no command that
actually runs a probe. The probe directory has 35 populated languages, one
20-item file, one 36-item file and nine empty files (`ab`, `af`, `ar`,
`en_US`, `hi`, `id`, `ro`, `sr`, `vi`).

## Goals / Non-Goals

**Goals:**

- One command from a deployment and language to a probe result and, when
  needed, a recorded pause.
- Budget enforcement before the first model request.
- A readable result and a machine-readable JSON form.
- Deterministic tests that never reach the network.

**Non-Goals:**

- Storing every passing probe as a historical baseline.
- Automatically re-qualifying a model after a pause.
- Resuming a paused release.
- Building a judge-preference probe; this command tests translation, not
  judging.

## Decisions

### Add a `drift` subcommand

`drift` matches the existing vocabulary (`drift_probe`, `drift_excursions`,
`po/drift-probe`, `--action drift`). A separate command keeps `estimate`
side-effect free and makes the spending step explicit, the same split used for
`qualify`.

### Infer the release from the deployment

A deployment already names exactly one release, and `load_config()` validates
that link. Taking a `--release` flag as well would allow the two to disagree,
so the handler reads `config.deployments[deployment_id].release` and forwards
it in the `DriftRequest`. The result still records the release.

### Probe path and empty probes

`--probe` overrides the path; otherwise the command uses
`DEFAULT_PROBE_DIR / f"{language}.json"`. An empty probe is rejected before
the run with a clear error, because `drift_probe()` would otherwise score it
0.0 and record a spurious pause. This matters for the nine languages that
currently have no probe items.

### Record pauses, not passes

A passing probe reports its score and writes nothing. A failing probe calls
`record_drift_excursion()` and writes the ledger. Recording every pass would
need a new section, a retention policy and a decision about which baseline a
later run compares against; none of that is required to pause new approvals.
The existing `costs` report already reads `drift_excursions` and keeps the
latest score per deployment.

### Audit-window start

`record_drift_excursion()` requires a `since` value. The command exposes
`--since`; it defaults to the run date. The operator can pass the date of the
last good probe or batch so the pause marks the right audit window. The
command does not guess the last good probe, because passing probes are not
stored.

### Dry run

`--dry-run` runs the probe and prints the result without writing a pause. It
is the useful form for screening a new model before qualification, where a
low score is a reason not to proceed rather than an operational pause.

### Exit status and output

The command exits `0` when the probe runs, including a below-threshold result
that records a pause; that is a valid outcome, and `--json` carries `paused`.
It exits non-zero only for an operational failure: unknown deployment, empty
or unreadable probe, missing credential, over-budget estimate or ledger write
failure. A `--require-pass` flag could be added later for shell gating.

The human form reports deployment, release, language, score, threshold, call
count, cost and whether the result paused. `--json` prints the full result,
including calls.

### Validate before reading, write only after success

The handler checks the deployment before reading the probe, so an unknown
deployment fails cheaply. `load_probe()` already reports missing or malformed
files as `GateError`. The ledger is written only after a paused result and
only when not in dry-run mode; an exception leaves the on-disk ledger
unchanged.

## Risks / Trade-offs

- **Small sample** -> a 40-item probe is a smoke test, not a quality
  certification. Its confidence interval near the threshold is wide. Document
  that qualification remains the real per-language check, and use the probe
  for triage and regression detection.
- **Exact-match scoring** -> a semantically correct but differently worded
  translation counts as wrong. The threshold is calibrated for a fixed probe,
  not for absolute quality claims.
- **Repeated failing runs** -> each run appends a paused record with its call
  evidence, so repeated failures grow the ledger. The command documents this;
  a later change can add resolution and history semantics.
- **Empty probes** -> nine languages cannot be probed until human data exists.
  The command names the empty probe rather than recording a false pause.
- **No resume** -> a pause stays until a separate re-qualification and audit
  action resolves it. Intentionally outside this change.
- **Credential leakage** -> the command uses the existing client, which reports
  only the missing variable name and never its value.

## Migration Plan

No migration. The command is additive and the ledger schema already allows
`drift_excursions`. Rollback is removing the subparser and handler; existing
pause records remain valid.

## Open Questions

None.
