# Proposal

## Why

The gate can detect drift with a fixed, stratified probe of up to 40 human
translations and record a paused excursion, but the only command-line surface
is `estimate --action drift`, which never calls a model. Running the probe
requires importing `drift_probe()` in ad-hoc Python, so drift detection is easy
to skip and leaves no repeatable path from a probe file to a pause.

A probe is also the cheapest way to screen a model before full qualification:
one language costs roughly $0.001 for the low-price deployments and $0.004 for
the judge, while covering the short-label, sentence, placeholder, plural and
high-impact strata.

## What Changes

- Add a `drift` subcommand to `dev/translation_gate.py`.
- It infers the release from the deployment, loads
  `po/drift-probe/<language>.json` by default, enforces an optional
  `--max-cost`, runs the fixed probe, and prints the score, threshold, call
  count and cost.
- When the score is below the threshold, it records a paused excursion in the
  ledger with the score, cost and audit-window start (`--since`, default
  today), without demoting existing approvals.
- Support `--probe`, `--max-cost`, `--since`, `--dry-run` and `--json`.
- Report operational failures cleanly and leave the ledger unchanged: unknown
  deployment, unreadable probe, missing credential or an over-budget estimate.
- Document the probe workflow in `po/README.md`.

Out of scope: storing every passing probe as a historical baseline, automatic
re-qualification, and resuming a paused release. Those are separate changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `machine-translation-gate`: add a requirement that the fixed drift probe is
  runnable from the command line, records a pause on a below-threshold score,
  and honors the budget before calling a model.

## Impact

- `dev/translation_gate.py`: new subparser, handler and help text.
- `dev/tests/test_translation_gate.py`: command, pause, error-path and output
  tests.
- `po/README.md`: drift command documentation.
- Ledger: appends a `drift_excursions` record when a probe pauses.
- No change to the shipped `scantpaper` package; this is maintainer tooling.
- No new dependency.
