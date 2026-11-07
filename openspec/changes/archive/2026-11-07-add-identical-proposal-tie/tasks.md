# Tasks

## 1. Tie detection

- [x] 1.1 After the deterministic checks, detect when every passing proposal
  has the same trimmed text and at least two independent families proposed;
  skip `blind_judge` for that tie, select the first passing proposal and
  record the `identical` verdict. Verify tests for a tie, a differing-proposal
  judge path, a single passing proposal and a failing check.
- [x] 1.2 Record the tie in the approval evidence
  (`judge.tie`, `judge.verdict`, `judge.families`) and verify the approval
  record and `record_gate_run` contain no judge call for a tie.

## 2. Sentence and provenance behaviour

- [x] 2.1 Keep the back-translation for a sentence tie; verify a passing
  sentence tie calls the back-translator and a failing back-translation still
  abstains.
- [x] 2.2 Keep `machine-strong` and `tm-consensus` selection unchanged for a
  tie; verify a dominant translation-memory match still records
  `tm-consensus`.

## 3. Documentation

- [x] 3.1 Document the tie rule and its cost rationale in `po/README.md`,
  including that a tie still requires two independent families and a sentence
  back-translation; verify the documented behaviour matches the gate.

## 4. Integration verification

- [x] 4.1 Run `pytest`, `ruff format --check .`, `ruff check .`, `ty check .`,
  `python3 dev/check_test_coverage.py` and
  `openspec validate add-identical-proposal-tie --strict --no-interactive`;
  verify all pass and coverage does not regress.

## Workflow follow-up

- Archive the change after review.
- Consider a separate change for judge selection and judge token budgets.
