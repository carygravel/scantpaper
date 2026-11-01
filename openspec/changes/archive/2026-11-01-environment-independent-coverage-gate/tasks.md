# Tasks

## 1. Relocate developer-tooling tests

- [x] 1.1 Create `dev/tests/` and move `test_build_ppa.py`,
  `test_prepare_deb.py` and `test_prepare_rpm.py` into it; change each
  module's `REPO_ROOT` from `parents[3]` to `parents[2]`. Verify each file
  passes when invoked by path from the repository root.
- [x] 1.2 Move `test_sync_salsa.py`, `test_release.py`, `test_launchpad.py`
  and `test_strip_remote_images.py` to `dev/tests/` and adjust their
  `REPO_ROOT` the same way. Verify each file passes and that
  `test_po_files.py` and `test_openspec_specs.py` remain in
  `src/scantpaper/tests/`.
- [x] 1.3 Extend the existing pytest per-file ignores in `pyproject.toml` to
  `dev/tests/**`, using the same rule list as `src/scantpaper/tests/**` and
  adding no new suppressions. Verify `ruff check .` and
  `ruff format --check .` are clean.
- [x] 1.4 Create `src/scantpaper/tests/test_coverage_config.py` with layout
  assertions proving the seven moved modules exist under `dev/tests/` and
  not under `src/scantpaper/tests/`. Verify the test fails if one module is
  moved back.
- [x] 1.5 Verify default collection is unchanged: run
  `python3 -m pytest --collect-only -q` before and after the move and
  confirm the same collected count, with the `dev/tests/` modules present in
  the node list.

## 2. Coverage total and test-code audit

- [x] 2.1 Add `[tool.coverage.report] omit` in `pyproject.toml`, add
  `--cov=dev/tests` to the pytest `addopts` so the relocated tests are
  recorded, keep `[tool.coverage.run] branch = true`, and leave the run
  section without an omit entry. Omit both test roots at report level
  (`*/scantpaper/tests/*`, `*/dev/tests/*`), with a comment that the report
  omits test code while the data stays available for the audit. Verify a
  full `pytest` run passes the gate and that
  `python3 -m coverage report -m` lists application modules only, with zero
  missing lines and no more than 175 partial branches.
- [x] 2.2 Extend `test_coverage_config.py` to assert that the report omit
  pattern matches a path under `src/scantpaper/tests/` and that the run
  section has no omit entry. Verify the test fails when the pattern is
  removed, and when it is moved into `[tool.coverage.run]`.
- [x] 2.3 Implement `dev/check_test_coverage.py`: enumerate every `.py`
  under `src/scantpaper/tests/` and `dev/tests/`, open `.coverage` with
  `Coverage(config_file=False, branch=True)`, and fail with a clear message
  when the data file is missing, a module is absent from the measured set,
  or a module has missing statements. Report partial branches and fail when
  they exceed the recorded baseline of 85. Verify it passes after a full
  run, fails after a partial run such as `pytest -k test_basic`, and fails
  when a test helper is temporarily left uncalled.
- [x] 2.4 Add `dev/tests/test_check_test_coverage.py` covering the pass
  case, an unmeasured module, a missing statement, and a partial-branch
  overrun. Verify the file passes and that it is collected by the default
  run.
- [x] 2.5 Add the audit step to the `latest` job in
  `.github/workflows/test.yml`, running
  `python3 dev/check_test_coverage.py` after `pytest`. Verify the step
  exists only in `latest` and follows the test step.
- [x] 2.6 Confirm and record the two baselines: the application gate shows
  zero missing lines and at most 175 partial branches; the test audit shows
  zero missing statements and 85 partial branches. Note any difference from
  `design.md` in the change discussion.

## 3. Debian autopkgtest dependencies

- [x] 3.1 Add `git` to `Depends` in `packaging/debian/tests/control`.
  Verify the file still lists `@` and the existing tools, and that
  `packaging/debian/control` does not gain a runtime dependency on git.
- [x] 3.2 Extend `src/scantpaper/tests/test_packaging_versions.py` to assert
  that the autopkgtest control declares `git` and that the runtime control
  does not. Verify the assertion fails when `git` is removed.
- [x] 3.3 Verify the now-runnable tests pass with git available: run the
  seven modules under `dev/tests/` and confirm none skip for a missing git,
  while `test_openspec_specs.py` still skips with its tooling reason.

## 4. Integration verification

- [x] 4.1 Simulate the previous Debian selection by running
  `pytest --ignore=dev/tests` and confirm the reported application coverage
  equals the full-run percentage. This is the regression check for the
  original 98.39% failure.
- [x] 4.2 Run the complete `pytest` suite followed by
  `python3 dev/check_test_coverage.py`: all tests pass, the gate is at or
  above 99%, and the audit reports zero missing test statements. Confirm the
  audit fails if a test module is deselected from that run.
- [x] 4.3 Run `ruff check .`, `ruff format --check .` and `ty check .`; all
  are clean.
- [x] 4.4 Update the testing section of `AGENTS.md` to state that the
  coverage gate measures only the application package, that test code is
  audited by `dev/check_test_coverage.py` after a full run, and that
  developer-tooling tests live under `dev/tests/`. Verify Markdown lines
  stay within 80 characters.
- [x] 4.5 Validate the change with
  `openspec validate environment-independent-coverage-gate --strict
  --no-interactive` and confirm it reports no issues.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result moves the delta specs into `openspec/specs/`.
