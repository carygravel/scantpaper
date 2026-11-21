# Tasks

## 1. Faithful validation harness

- [x] 1.1 Create a throwaway venv mirroring `lint-check.yml` (fresh venv
  with `--system-site-packages`, `pip install '.[test]'`, then latest
  unpinned `ruff` and `ty`), and verify
  `/tmp/opencode/ci-faithful/bin/ruff --version` reports `0.17.6` and
  `/tmp/opencode/ci-faithful/bin/ty --version` reports `0.0.107`
- [x] 1.2 Confirm the current broken state reproduces in that venv and
  record its output: `ruff check .` fails with 28 `ICN001` + 1 `RUF012`,
  `ruff format --check .` passes, and `ty check .` fails with 403
  `missing-union-attribute` + 7 other diagnostics

## 2. ty configuration migration (prepared, verified, lands atomically with the pin)

- [x] 2.1 Verify the renamed-key migration in the harness venv WITHOUT yet
  editing `pyproject.toml`: run ty 0.0.107 with
  `-c "rules.missing-attribute='ignore'" -c
  "rules.missing-union-attribute='ignore'"` overrides and confirm the 403
  `missing-union-attribute` errors and the `warning[renamed-rule]` both
  disappear, leaving exactly the 7 individual diagnostics listed under
  tasks 3–8
- [x] 2.2 Confirm the migration is version-bound: verify that keeping the
  OLD config means the pinned ty 0.0.85 stays green (no `unknown-rule`
  warnings and no `unresolved-attribute` flood) in a faithful venv, so the
  old gate remains clean at every intermediate commit until the atomic
  config+pin step (task 9.2)

## 3. Simplelist redundant casts

- [x] 3.1 Remove the redundant `cast("Iterator[object]", ...)` wrapper in
  `src/scantpaper/simplelist.py:191`, keeping the return annotation, and
  verify the `redundant-cast` diagnostic disappears under ty 0.0.107 (with
  the `-c` rules overrides from 2.1, as the config file is not yet
  migrated)
- [x] 3.2 Remove the redundant `cast("Iterator[list[object]]", ...)`
  wrapper in `src/scantpaper/simplelist.py:415`, and verify the second
  `redundant-cast` diagnostic disappears (same override invocation)
- [x] 3.3 Verify the full suite still passes (`pytest`) since `typing.cast`
  is a runtime no-op and iteration semantics are unchanged

## 4. Canvas unsound return

- [x] 4.1 Annotate `self._bbox` as `list[Bbox]` at its first assignment in
  `TreeIter.__init__` (`src/scantpaper/canvas.py:1831`), and verify ty
  0.0.107 (with the `-c` rules overrides from 2.1) no longer reports
  `unsound-return` at line 1850; if the reassignment still narrows, fall
  back to the file's existing `cast("Bbox", ...)` idiom on the return
- [x] 4.2 Verify `pytest` still passes and the iterator's navigation tests
  (first/next/previous bbox) still behave identically

## 5. Bboxtree heterogeneous dict typing

- [x] 5.1 Add `self.data: dict[str, object] = {}` to
  `PDFTextParser.__init__` (`src/scantpaper/bboxtree.py`), mirroring
  `HOCRParser`'s declaration so ty stops narrowing the dict to
  `dict[str, list[float]]`, and verify the three `invalid-assignment`
  diagnostics at lines 631, 647, and 680 disappear under ty 0.0.107 (with
  the `-c` rules overrides from 2.1); if a rebind still narrows, apply the
  `cast("dict[str, object]", ...)` fallback at those subscript assignments
- [x] 5.2 Verify `pytest` passes, including the hOCR/PDF-text parser tests
  that assert on parsed bounding boxes and text

## 6. BaseThread class-registry annotation

- [x] 6.1 Import `ClassVar` and annotate
  `LiveThreads: ClassVar[weakref.WeakSet[BaseThread]] = weakref.WeakSet()`
  in `src/scantpaper/basethread.py:119`, and verify the `RUF012` finding
  disappears under `ruff check` 0.17.6
- [x] 6.2 Verify the suite still passes, including the base-thread tests
  that quit lingering worker threads through the live-thread registry

## 7. Conventional datetime import alias

- [x] 7.1 Rename `import datetime` to `import datetime as dt` in the 18
  `src/scantpaper` files, and verify `ruff check --select ICN001` 0.17.6
  reports no remaining hits there (autofix with `--fix --unsafe-fixes` and
  review the diff; update usages so the module is referenced as `dt`)
- [x] 7.2 Rename the import in the 10 `src/scantpaper/tests/` and `dev/`
  files, and verify `ruff check --select ICN001` 0.17.6 reports no
  remaining hits anywhere and `ruff format --check .` passes
- [x] 7.3 Verify `pytest` passes and that no file regressed to a bare
  `import datetime` (the project already aliases it as `dt` in one test)

## 8. Test truthiness equivalence

- [x] 8.1 Change the truthiness test in
  `src/scantpaper/tests/test_0821_frontend_image_sane.py:1046` from
  `if r.exc_info` to `if r.exc_info is not None`, and verify the
  `truthiness-test-of-none-union` diagnostic disappears under ty 0.0.107
  (with the `-c` rules overrides from 2.1)
- [x] 8.2 Verify the feeder-empty logging assertions still pass (`pytest`),
  confirming a record with a traceback is still matched

## 9. Atomic config+pin adoption and integrate

- [x] 9.1 In the same commit, migrate `[tool.ty.rules]` in
  `pyproject.toml` to the renamed keys (`missing-attribute` and
  `missing-union-attribute`, replacing `unresolved-attribute`) AND bump
  `dev/lint-versions` to `ruff=0.17.6` and `ty=0.0.107`; verify
  `grep '^ruff=' dev/lint-versions | cut -d= -f2` and the ty equivalent
  print exactly those versions, and that the migrated rules text is present
- [x] 9.2 Re-run all gates in the harness venv with the latest tools and
  confirm they are clean: `ruff check .`, `ruff format --check .`, and
  `ty check .` all exit 0 with the migrated config now in place and the
  source fixes applied
- [x] 9.3 Install the newly pinned versions in the project `.venv`
  (`pip install "ruff==0.17.6" "ty==0.0.107"`) and verify
  `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, and
  `.venv/bin/ty check .` all pass, matching what CI will run
- [x] 9.4 Run the full suite `pytest` from the repository root and verify
  it passes, and run `dev/check_test_coverage.py` and confirm the
  uncovered/partially-covered counts are the same or better than before
- [x] 9.5 Run `openspec validate --specs --strict --no-interactive` and
  `openspec validate --archived --no-interactive` and verify both pass,
  and confirm the `update-lint-tools` change itself validates with its
  `skip_specs: true` marker

## Workflow follow-up

- Push the adoption; `test.yml` installs the new pins automatically.
- Confirm the scheduled `lint-check` run reports `safe to upgrade` and
  closes the `lint-update` issue once the pins match `latest`.
- Archive the change after review.
