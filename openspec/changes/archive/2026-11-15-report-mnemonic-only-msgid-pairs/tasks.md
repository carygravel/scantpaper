# Tasks

## 1. Regression tests (TDD)

- [x] 1.1 Add a test in `src/scantpaper/tests/test_po_files.py` that a
      source set containing `Copy` and `_Copy` produces one advisory line
      naming both, and validation exits successfully.
- [x] 1.2 Add a test that `Cu_t` with `Cut`, and `Zoom _in` with
      `Zoom in`, each produce their own group, so a marker anywhere in the
      msgid is found.
- [x] 1.3 Add negative tests that `Save` with `Save as…` produces no group,
      and that a catalog translating a single msgid with a relocated marker
      produces none either. These guard against over-reporting and become
      meaningful only once 2.1 exists; confirm 1.1 and 1.2 fail before the
      change.

## 2. Report

- [x] 2.1 Add the marker-removal grouping and its advisory line to the
      source-wide reports in `dev/check_po.py`; verify 1.1 to 1.3 pass.
- [x] 2.2 Run `PYTHONPATH=src python3 dev/check_po.py` on the real source
      tree and confirm it names the 34 existing groups, that the other
      advisory lines are unchanged, and that it exits 0.

## 3. Integration and quality gates

- [x] 3.1 Run the full `pytest` suite and confirm the coverage gate passes.
- [x] 3.2 Run `python3 dev/check_test_coverage.py` and confirm the counts
      are at or below the recorded baseline.
- [x] 3.3 Run `ruff format` and `ruff check` and confirm both are clean.
- [x] 3.4 Run `ty check .` and confirm there are no diagnostics.
- [x] 3.5 Run `openspec validate --specs --strict --no-interactive` and
      `openspec validate --archived --no-interactive` and confirm both pass.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
