# Tasks

## 1. Command surface and core run

- [x] 1.1 Add the `drift` subparser with `--deployment`, `--language`,
  `--probe`, `--max-cost`, `--since`, `--dry-run` and `--json`, and verify
  `python3 dev/translation_gate.py drift --help` lists every option.
- [x] 1.2 Implement the handler: validate the deployment, infer its release,
  load the default or explicit probe, reject an empty probe, load the ledger,
  estimate and enforce the budget, and run `drift_probe`; verify a test with a
  fake client reports the score and makes exactly one call per probe item.
- [x] 1.3 Record a paused excursion with the supplied `--since` or the run
  date, skip the write under `--dry-run`, and print a human summary; verify a
  passing probe writes nothing, a failing probe pauses the language, and a
  dry run leaves the ledger unchanged.

## 2. Edge cases and output

- [x] 2.1 Cover an unknown deployment, an empty probe, an unreadable probe, a
  missing key environment variable and an over-budget estimate; verify each
  exits non-zero, reports the cause and leaves the ledger unchanged.
- [x] 2.2 Cover the JSON form and confirm it contains the inferred release,
  score, threshold, `paused` flag, call count and cost.
- [x] 2.3 Verify a paused probe does not demote an existing approval and that
  a repeated failing run still leaves the language paused.

## 3. Documentation

- [x] 3.1 Document `drift` in the drift section of `po/README.md`, including
  the estimate-first workflow, dry-run screening for new models, `--since`,
  the nine empty probe languages and the no-resume limitation; verify the
  documented command matches the parser.

## 4. Integration verification

- [x] 4.1 Run `pytest`, `ruff format --check .`, `ruff check .`, `ty check .`,
  `python3 dev/check_test_coverage.py` and
  `openspec validate add-drift-probe-command --strict --no-interactive`;
  verify all pass and coverage does not regress.

## Workflow follow-up

- Archive the change after review.
- Consider separate changes for storing passing probes, resuming a pause and
  building a judge-preference probe.
