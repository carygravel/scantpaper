## 1. Regression test for the bug

- [x] 1.1 Add a regression test: after a page switch, `_on_page_loaded`
      re-applies the selection against the full-resolution image, so the
      selection stays valid (width/height > 0) rather than being clamped away
      by the transient thumbnail
- [x] 1.2 Add a test that `settings["selection"]` is not overwritten with a
      degenerate rectangle during the page-change flow

## 2. Re-apply selection on full-resolution load

- [x] 2.1 In `_on_page_loaded` (`session_mixins.py`), after the full-resolution
      pixbuf is set, re-apply `settings["selection"]` (when set) via
      `view.set_selection`, so it is clamped to the real image size
- [x] 2.2 Add a test for `_on_page_loaded` reapplying a valid, bounded
      selection after the full-resolution page loads

## 3. Stop clamping against the thumbnail

- [x] 3.1 Remove the `if sel is not None: self.view.set_selection(sel)` block
      from `_page_selection_changed_callback` (`app_window.py`), so the
      selection is no longer re-applied against the thumbnail-only state
- [x] 3.2 Update the test in `test_app_window.py` verifying that switching
      pages does not clamp the selection to a degenerate size or corrupt
      `settings["selection"]`

## 4. Quality gates

- [x] 4.1 Run `ruff format` and `ruff check` on changed files; fix any
      violations
- [x] 4.2 Run `ty check .` and fix any diagnostics
- [x] 4.3 Run the full `pytest` suite; confirm coverage thresholds are met and
      no uncovered lines are introduced outside `TYPE_CHECKING` imports
