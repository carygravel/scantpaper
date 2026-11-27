# Tasks

## 1. Capture the effective mode and depth at scan start

- [x] 1.1 In `src/scantpaper/dialog/sane.py`, add a helper that reads the
      effective `mode` and `depth` option values from the backend via
      `thread.get_option_value`, tolerating a missing/inactive option (returns
      `None`) so a scanner with no such option stays a safe "not requested"
      default. Verify it returns `None` for an absent option and the backend
      value otherwise.
- [x] 1.2 In `SaneScanDialog.scan()` (`dialog/sane.py:564`), capture the
      effective mode and depth once at batch start (alongside
      `_get_xy_resolution()`), and pass them into `new_page_callback`.
      Verify the values are captured once per batch, not per page.
- [x] 1.3 Update `_depth_mismatch` (`dialog/sane.py:670`) to decide the
      1-bit request from the captured effective depth/mode instead of
      `current_scan_options`: delivered `"1"` stays unconverted, effective
      `depth == 1` or an effective bilevel `mode` converts, anything else is
      unconverted. Reuse `_BILEVEL_MODE_RE` unchanged. Verify the existing
      bilevel/continuous-tone outcomes still hold.

## 2. Tests

- [x] 2.1 Adapt the `sane_scan_mocks` device handle in
      `src/scantpaper/conftest.py` (`mocked_do_open_device`) so it can report
      a `mode` and `depth` via `get_option_value` (both when left at a default
      and after `set_option_in_mainloop` sets them through
      `mocked_do_set_option`). Verify `set_option_in_mainloop(dialog, "mode",
      "Lineart")` is reflected in `thread.get_option_value("mode")`.
- [x] 2.2 Rework `test_new_scan_enforce_depth`
      (`test_0610_dialog_scan_sane.py:1842`) so its cases drive the effective
      mode/depth through the backend value rather than the profile, keeping
      every existing row's expected outcome. Verify the full table passes.
- [x] 2.3 Add a regression case: backend default mode is bilevel (e.g.
      `mode="Lineart"`) and the user scans without touching the mode - the
      delivered 8-bit frame must be converted (warning logged, page 1-bit).
      Verify the new case passes and fails on the pre-change code path.

## 3. Integration verification

- [x] 3.1 Run `pytest` from the repository root and confirm all tests pass
      with the coverage gate (uncovered/partially covered lines no worse than
      baseline).
- [x] 3.2 Run `ruff check .` and `ty check .`; confirm no diagnostics, then
      run `python3 dev/check_test_coverage.py` and confirm no new unexecuted
      statements.
- [x] 3.3 Document the fix in `README.md` and `changelog.md` if any
      user-visible behaviour changed. `README.md` already described the
      intended behaviour, so only `changelog.md` gained an entry (in the
      already-released 4.0.4 section). No translation change: the warning
      and notice text are reused.

## Workflow follow-up

- Validate both `openspec validate --specs --strict --no-interactive` and
  `openspec validate --archived --no-interactive` before pushing.
- Archive the change after review.
