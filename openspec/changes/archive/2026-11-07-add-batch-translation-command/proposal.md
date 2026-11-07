# Proposal

## Why

The gate can review one string at a time, but the catalogs still have
hundreds of fuzzy proposals and 131 template msgids are absent from every
catalog. `gate` writes a decision for one msgid, `approve` applies one
msgid, and `approve` currently only clears the fuzzy flag; it does not write
the approved text into an empty entry. Clearing the missing translations at
scale is therefore not possible today.

The first targets are the English and German catalogs: `en_GB`, `en_US` and
`de`. There is no `en.po`; the English catalogs are the `en_GB`/`en_US`
variants.

## What Changes

- Add a `translate` subcommand that selects empty entries (and optionally
  fuzzy proposals) in one catalog, runs the gate for each, writes each
  approved translation into the catalog, clears fuzzy, and records the
  approval.
- Leave abstained entries fuzzy and report them.
- Refuse to run when any proposer or judge release is not qualified for the
  language or when the language is paused for drift; tell the operator which
  `qualify` or `drift` step is missing.
- Estimate the selected batch before any call and enforce an optional total
  `--max-cost`; stop before the next entry would exceed the budget.
- Pass each entry's occurrences and an optional `--tm` database so
  high-impact classification and `tm-consensus` behave as they do in the
  library.
- Support `--limit`, `--include-fuzzy`, `--dry-run` and `--json`.
- Fix the apply path so an approved decision writes `msgstr`, not just clears
  fuzzy. This also fixes the existing `approve` command for empty entries.
- Document the first-run workflow and record that `machine-strong` is
  acceptable for high-impact menu and destructive strings.

Out of scope: translating plural entries and entries with a message context.
The template has two plural entries and no contexts; the command reports
unsupported entries and leaves them unchanged. A separate change can add
them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `machine-translation-gate`: add requirements for applying the approved
  text, batch catalog translation, qualification and drift guards, and a
  total budget.

## Impact

- `dev/translation_gate.py`: new subparser, handler, apply helper and
  `approve` fix.
- `dev/tests/test_translation_gate.py`: apply, batch, guard, budget, dry-run
  and JSON tests.
- `po/README.md`: first-run targets, batch workflow and the high-impact
  policy.
- `po/scantpaper/en_GB.po`, `en_US.po` and `de.po`: updated only when the
  command is run.
- No new dependency and no shipped `scantpaper` change.
