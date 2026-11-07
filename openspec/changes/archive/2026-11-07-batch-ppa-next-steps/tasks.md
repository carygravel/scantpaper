# Tasks

## 1. Pin the grouped output with tests

- [x] 1.1 Add a two-series `--dry-run` test in
  `dev/tests/test_build_ppa.py` asserting one `Next steps:` header, both
  `dput` lines in selection order, and the header after both `prepared`
  lines; verify the test fails against the current per-series printing.
- [x] 1.2 Add a two-series build test using the existing fake `debuild`
  pattern, asserting one block with the actual `.changes` paths in
  selection order; verify it fails before the implementation change.
- [x] 1.3 Add partial-failure tests with a fake `debuild` that fails for one
  series: a later failure prints the earlier series' `dput` once, omits the
  failed series, and exits non-zero; a first-series failure prints no
  `Next steps:` header. Verify both fail before the implementation change.

## 2. Collect and print the next steps once

- [x] 2.1 Make `_build_series` return the `.changes` path (actual after a
  build, predicted for `--dry-run`), accumulate the paths in `build`, and
  print one `Next steps:` block in a non-empty-guarded `finally` around the
  series loop; verify every test in `dev/tests/test_build_ppa.py` passes,
  including the new grouped and partial-failure cases.
- [x] 2.2 Confirm the block uses the selection order, keeps the existing
  `dput <target> <changes>` form, and leaves progress lines, signing, exit
  status, and `dev/sync_salsa.py` untouched; verify with the two-series
  build test and a clean `git diff` review of the untouched paths.

## 3. Document the output

- [x] 3.1 Update the PPA paragraph in `release_procedure.md` to say the
  `dput` commands are printed together at the end, including for series that
  finished before a later failure; verify the wording matches the behavior
  in the new tests.

## 4. Quality gates and validation

- [x] 4.1 Run `ruff format`, `ruff check`, and `ty check .`; verify no
  diagnostics or formatting changes remain.
- [x] 4.2 Run `pytest` and then `python3 dev/check_test_coverage.py`; verify
  the suite passes, the 99% gate holds, and no new unexecuted test statements
  appear.
- [x] 4.3 Run
  `openspec validate --specs --strict --no-interactive` and
  `openspec validate batch-ppa-next-steps --strict --no-interactive`; verify
  both pass.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
