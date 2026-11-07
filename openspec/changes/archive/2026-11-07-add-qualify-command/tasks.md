# Tasks

## 1. Command surface and core run

- [x] 1.1 Add the `qualify` subparser with `--release`, `--language`,
  `--catalog`, `--count`, `--max-cost` and `--json`, and verify
  `python3 dev/translation_gate.py qualify --help` lists every option.
- [x] 1.2 Implement `_command_qualify` to validate the release, load the
  ledger and catalog, select held-out entries, estimate and enforce the
  budget, call `qualify_release` with the real client and write the ledger;
  verify a test with a fake client stores `qualified: true` and the score.
- [x] 1.3 Print a human summary with release, language, score, tolerance,
  baseline size, deployment, cost and outcome, and print the full record with
  `--json`; verify both forms with captured output in the tests.

## 2. Edge cases and ledger safety

- [x] 2.1 Cover a score below the tolerance and a language with no held-out
  human entries; verify the first records `qualified: false`, the second
  records `no held-out human entries`, and neither calls a model for the
  empty baseline.
- [x] 2.2 Cover an unknown release, an unreadable catalog, a missing key
  environment variable and a non-positive `--count`; verify each exits
  non-zero, reports the cause and leaves the ledger file unchanged.
- [x] 2.3 Cover an over-budget estimate; verify no model call is made and no
  record is written.
- [x] 2.4 Cover a repeated run for the same release and language; verify the
  ledger keeps exactly one qualification record for the pair, updated to the
  latest result.

## 3. Documentation

- [x] 3.1 Document `qualify` in the qualification section of `po/README.md`,
  including the estimate-first workflow and the no-baseline outcome; verify
  the documented command matches the parser.

## 4. Integration verification

- [x] 4.1 Run `pytest`, `ruff format --check .`, `ruff check .`, `ty check .`,
  `python3 dev/check_test_coverage.py` and
  `openspec validate add-qualify-command --strict --no-interactive`; verify
  all pass and coverage does not regress.

## Workflow follow-up

- Archive the change after review.
- Consider a separate change that makes `gate` consult the qualification
  record, which this change deliberately leaves out.
