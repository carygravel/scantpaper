# Tasks

## 1. Strict-mode hooks

- [x] 1.1 Add a new root `conftest.py` with `pytest_addoption` for
  `--fail-on-skip`, the per-session skip store on `config`,
  `_fail_on_skip_enabled` (flag or `SCANTPAPER_FAIL_ON_SKIP=1`), and
  `_skip_reason`; verify unit tests in
  `src/scantpaper/tests/test_fail_on_skip.py` load the root conftest with
  `importlib` and cover the flag, the variable, both, neither, `"0"`,
  `"1"`, and both skip representations.
- [x] 1.2 Add `pytest_runtest_makereport` to record setup and call skips
  on `item.config`, deduplicate by node id, and ignore passes, xfail
  reports, and other phases; verify unit tests cover each case.
- [x] 1.3 Add `pytest_terminal_summary` and `pytest_report_header`;
  verify unit tests assert every node id and reason appears in the
  summary and the header appears only when a switch is set.
- [x] 1.4 Add `pytest_sessionfinish` to fail an `OK` session when skips
  were recorded, preserve an existing non-zero status, no-op when
  disabled, when no skip was recorded, or for an `xdist` worker, and
  write the summary to stderr when no terminal reporter is present;
  verify each branch with unit tests.
- [x] 1.5 Add a subprocess integration test that copies the root
  conftest into a temporary directory with a small file containing a
  marker skip and an `importorskip` guard, and runs `python -m pytest`
  there with `PYTHONPATH` pointing at `src`; verify exit 1 and both
  reasons with `--fail-on-skip` and with `SCANTPAPER_FAIL_ON_SKIP=1`,
  exit 0 with neither, and no failure for a `-m`-deselected,
  `--ignore`d, or xfailed test.

## 2. Documentation

- [x] 2.1 Update the README Testing section with both switches and a
  canonical-environment dependency list covering the `de_DE.utf8`
  locale, `tesseract` with German data, `unpaper`, `cjb2`, `qpdf`,
  `pdfunite`, `pdftoppm`, `jbig2`, a display, `git`, `appstreamcli`,
  `desktop-file-validate`, `msgfmt`, ImageMagick's `convert`, the DejaVu
  fonts, and the `openspec` CLI; verify the documented flag, variable
  and command match the implementation and the list matches the probes
  in the suite's skip guards and import guards.
- [x] 2.2 Update the AGENTS.md testing workflow with the
  canonical-environment-only rule and the supported-floor and
  third-party-tool exceptions; verify it names both switches and both
  exceptions.

## 3. CI and Debian enablement

- [x] 3.1 Add `desktop-file-utils` to `packaging/debian/tests/control`;
  verify the rendered control declares it and
  `dev/tests/test_join_metadata.py` runs all 12 tests with no skip.
- [x] 3.2 Set `SCANTPAPER_FAIL_ON_SKIP: "1"` on the `Test` step of the
  `latest`, `stonking`, and `resolute` jobs; verify each job reports no
  skipped tests (run `pytest -rs` in an equivalent environment or inspect
  the job log) before merging.
- [x] 3.3 Update `packaging/debian/tests/test-suite` to run
  `pytest --fail-on-skip
  --ignore=src/scantpaper/tests/test_openspec_specs.py`; verify the
  autopkgtest passes and reports no skipped tests, with the ignored
  third-party module absent rather than skipped.
- [x] 3.4 Leave the `noble` and `jammy` jobs without the switch and add
  a workflow comment explaining the expected skips; verify by inspecting
  the workflow.

## 4. Integration verification

- [x] 4.1 Run the full suite without a switch and confirm the result is
  unchanged, then run it with `--fail-on-skip` and with
  `SCANTPAPER_FAIL_ON_SKIP=1` in the local complete environment and
  confirm there are no skips.
- [x] 4.2 Run `ruff check .`, `ruff format --check .`, `ty check .`, and
  `python3 dev/check_test_coverage.py`; verify none reports an error and
  the coverage and audit numbers are unchanged or better.
- [x] 4.3 Run
  `openspec validate "fail-on-skipped-tests" --strict --no-interactive`,
  `openspec validate --specs --strict --no-interactive`, and
  `openspec validate --archived --no-interactive`; verify all pass.

## Workflow follow-up

- Archive the change after the project's review requirements are
  satisfied.
- Verify the archived result.
