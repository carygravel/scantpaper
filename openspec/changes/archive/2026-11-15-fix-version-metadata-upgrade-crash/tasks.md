# Tasks

## 1. Application version resolution

- [x] 1.1 Add failing tests in
  `src/scantpaper/tests/test_const.py` for the version chain: a source
  `pyproject.toml`, valid installed metadata, `version()` returning
  `None`, `PackageNotFoundError`, recovery from a later valid
  distribution, and the unknown fallback. Add a CLI test in
  `src/scantpaper/tests/test_app.py` asserting `--version` prints the
  resolved value and the fallback without raising. Verify the new tests
  fail for the expected reasons before implementation.
- [x] 1.2 Add `UNKNOWN_VERSION` and implement the
  `pyproject.toml` -> `importlib.metadata.version()` ->
  `importlib.metadata.distributions()` scan -> fallback chain in
  `src/scantpaper/const.py`, using `metadata.get(...)` and catching
  `PackageNotFoundError`. Verify the tests from 1.1 pass.
- [x] 1.3 Confirm the window title, About dialog, saved PDF creator and
  saved hOCR `ocr-system` continue to use the resolved string, and that
  an unknown value is accepted there. Verify with the existing tests in
  `test_app_window.py`, `test_101_document.py`, `test_151_save_text.py`
  and `test_75_bboxtree.py`.

## 2. Config migration safety

- [x] 2.1 Extend `test_threshold_tool_migration` in
  `src/scantpaper/tests/test_8_config.py` with a config whose version is
  `"unknown"` and whose threshold is 20, asserting the threshold stays
  20. Verify the new case fails before the implementation.
- [x] 2.2 Update `_version_tuple()` in `src/scantpaper/config.py` so a
  present but unparseable version maps to a high sentinel while `None`
  still maps to `(0,)`. Verify 2.1 and the existing legacy, current and
  missing-version cases pass.

## 3. openSUSE directory ownership

- [x] 3.1 Add a failing test in
  `src/scantpaper/tests/test_packaging_opensuse.py` that every
  `packaging/opensuse/*.spec` generates a `%files` list covering
  directories under `%{python3_sitelib}` or `%{python3_sitearch}`.
  Verify the test fails before the spec edits.
- [x] 3.2 Add the directory `find` pass and update the `%install`
  comment in all ten `packaging/opensuse/*.spec` files, keeping shared
  system directories unowned. Verify the test from 3.1 passes.
- [x] 3.3 Update `packaging/opensuse/README.md` to explain why the file
  list owns site-packages directories, why shared system directories are
  excluded, and why Fedora and Debian do not need the same change.
  Verify the rationale matches the edited specs.

## 4. CI guards on both openSUSE targets

- [x] 4.1 Add failing tests in
  `src/scantpaper/tests/test_packaging_opensuse.py` asserting that both
  `.github/workflows/opensuse.yml` and
  `.github/workflows/opensuse-tumbleweed.yml` contain the metadata
  ownership assertion and the stale-metadata clean-room step. Verify the
  tests fail before the workflow edits.
- [x] 4.2 Add the ownership assertion to both workflows: for every built
  RPM, require `rpm -qpl` (or the equivalent mode query) to list a
  version-named `*.dist-info/` directory, naming the RPM on failure.
  Verify the ownership tests from 4.1 pass.
- [x] 4.3 Add the stale-metadata step to both clean-room jobs: capture
  the installed version, create an empty `scantpaper-0.0.0.dist-info` in
  the installed purelib, require `scantpaper --version` to be unchanged,
  then remove the directory. Verify the stale-metadata tests from 4.1
  pass and that the shell matches the design.

## 5. User documentation

- [x] 5.1 Add the stale-metadata symptom and the `rmdir` cleanup command
  to the installation/troubleshooting section of `README.md`, and note
  that the application now tolerates the directory. Verify the command
  removes an empty simulated `scantpaper-*.dist-info` and leaves a
  populated one alone.
- [x] 5.2 Add an entry to the unreleased section of `changelog.md`
  naming the upgrade crash, the fix and the cleanup workaround. Verify
  the entry is under the unreleased heading and wraps at 80 columns.

## 6. Integration checks

- [x] 6.1 Run `pytest` from the repository root and verify all tests
  pass with the project's coverage gate.
- [x] 6.2 Run `ruff format --check .`, `ruff check .` and `ty check .`
  and verify no diagnostics remain.
- [x] 6.3 Run
  `openspec validate fix-version-metadata-upgrade-crash --type change
  --strict --no-interactive` and verify it passes.
- [x] 6.4 Run `openspec validate --specs --strict --no-interactive` and
  `openspec validate --archived --no-interactive` and verify both pass.
- [x] 6.5 Push the branch and verify the Leap and Tumbleweed CI jobs
  pass, including the new ownership assertion and the stale-metadata
  clean-room step. Confirm the Fedora and Debian jobs remain green.

## Workflow follow-up

- Archive the change after the project's review requirements are met.
- Verify the archived result with
  `openspec validate --archived --no-interactive`.
