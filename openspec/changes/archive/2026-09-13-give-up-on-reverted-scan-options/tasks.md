## 1. Per-option revert tracking

- [x] 1.1 Write a failing unit test (using the existing
      `infinite_reloads_scan_mocks` fixtures) asserting that when a
      profile option is reverted by the backend on every reload, the option
      is set at most K=2 times during one top-level apply.
- [x] 1.2 Add per-dialog state `_reverted_option_counts` (a dict keyed by
      scan-option name) and a module constant for the per-option re-apply
      budget K, initialised with the other dialog state in
      `src/scantpaper/dialog/scan.py`.
- [x] 1.3 Add a helper that, given an option name, returns whether
      `count < K`, increments the count, and signals give-up otherwise.

## 2. Give-up and drop behaviour

- [x] 2.1 Write a failing unit test reproducing the coupled-options case from
      the Epson GT-20000 log: a mock backend where setting A reverts B and
      setting B reverts A (both return `INFO_RELOAD_OPTIONS`), asserting the
      apply terminates, one option is dropped, and the remaining options are
      still applied.
- [x] 2.2 In `_set_option_profile` (`src/scantpaper/dialog/scan.py:1210`),
      gate the `_set_option_with_hook` call (scan.py:1253) on the per-option
      budget from 1.3; on give-up, log a WARNING containing the option name
      and the word that the option is being dropped.
- [x] 2.3 On give-up, call `current_scan_options.remove_backend_option_by_name`
      on the live profile so later re-applies and config saves omit the
      dropped option.
- [x] 2.4 Write a failing unit test asserting that the dropped option is not
      written back when the current scan options are saved as
      `default-scan-options`.

## 3. Linear reload backstop

- [x] 3.1 Write a failing unit test asserting the total-reload budget is
      linear in the option count (3 * num_options) rather than triangular.
- [x] 3.2 Replace the `num * (num + 1) // 2` computation in the
      `available_scan_options` setter (`src/scantpaper/dialog/scan.py:355`)
      with `3 * num`.
- [x] 3.3 Adjust the `process-error` text (scan.py:722-731) so the global
      backstop message names the capped reload budget, keeping it as a last
      resort rather than the common failure path.

## 4. Counter reset semantics

- [x] 4.1 Write a failing unit test asserting a second `set_current_scan_options`
      call starts with fresh per-option counts after a pathological first
      apply.
- [x] 4.2 Reset `_reverted_option_counts` at the top of `set_current_scan_options`
      (`src/scantpaper/dialog/scan.py:1160`), and for the option being set in
      the user-initiated widget callbacks in `src/scantpaper/dialog/sane.py`
      (switch/button/spinbutton/combobox/entry callbacks at sane.py:246-328),
      mirroring the existing `num_reloads = 0` resets.
- [x] 4.3 Verify (with the existing `num_reloads = 0` resets) that
      `num_reloads` and the per-option counts are not cleared by the
      `available_scan_options` setter mid-apply (nested reload re-entry shares
      the top-level budget).

## 5. Existing test updates

- [x] 5.1 Update `src/scantpaper/tests/test_0608_dialog_scan.py` so
      `test_infinite_reloads` asserts per-option drop (small `num_reloads`,
      offending option dropped) instead of the old limit-error expectation.
- [x] 5.2 Review `src/scantpaper/tests/test_0601_dialog_scan.py` and
      `test_06093_dialog_scan.py` for assertions tied to the triangular limit
      or the old message and align them with the new semantics.

## 6. Verification and docs

- [x] 6.1 Run the full test suite with coverage and confirm no covered-line
      regressions (`pytest` per pyproject.toml).
- [x] 6.2 Run `ruff format` and `ruff check` on all touched files.
- [x] 6.3 Update README.md if any user-visible behaviour changed.