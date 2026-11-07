# Proposal

## Why

The gate can record a per-release, per-language qualification, but the only
command-line surface is `estimate --action qualification`. Running a real
qualification requires importing `qualify_release()` in ad-hoc Python, so the
step is easy to skip and leaves no reproducible, documented path from a
catalog to a ledger record.

## What Changes

- Add a `qualify` subcommand to `dev/translation_gate.py` that runs one
  qualification for a release and language.
- The command selects held-out human-origin approvals from the language
  catalog, estimates the action, enforces an optional `--max-cost` before any
  request, calls the release's deployment, writes the qualification record to
  the ledger, and prints a summary.
- Support `--catalog`, `--count`, `--max-cost` and `--json`, matching the
  existing qualification estimate.
- Report operational failures cleanly and leave the ledger unchanged: unknown
  release, unreadable catalog, missing credential or an over-budget estimate.
- Document the command in `po/README.md`.

Out of scope: making `gate` refuse to run without a qualification record. That
is a separate behavioral change with its own compatibility impact.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `machine-translation-gate`: add a requirement that qualification is runnable
  from the command line, records its result, cost and no-baseline outcome, and
  honors the budget before calling a model.

## Impact

- `dev/translation_gate.py`: new subparser, handler and help text.
- `dev/tests/test_translation_gate.py`: command, error-path and output tests.
- `po/README.md`: qualification command documentation.
- Ledger: adds or replaces a `qualifications` record for the selected
  `(release, language)` pair.
- No change to the shipped `scantpaper` package; this is maintainer tooling.
- No new dependency.
