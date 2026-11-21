# Tasks

## 1. Pointer anchoring

- [x] 1.1 In `app_window._handle_clicks`, translate the gesture point
      `(x, y)` from the clicked widget into the window coordinate space
      (`widget.compute_point(self, GdkPoint(...))`) and, for both the
      image-view and thumbnail-list popovers, call `set_pointing_to(rect)`
      before `popup()`; `popdown()` first when the popover is already
      visible so a second right-click re-anchors. Verify: `test_handle_clicks`
      (updated in 2.1) passes.
- [x] 1.2 Guard the translation: if `compute_point` raises or returns
      None, fall back to showing the popover at the window origin instead
      of crashing. Verify: a unit test forces the failure path (mock
      `compute_point` to raise) and asserts no exception escapes
      `_handle_clicks`.

## 2. Tests

- [x] 2.1 Extend `test_handle_clicks` for both popovers to assert that
      `set_pointing_to` is called with a 1x1 rectangle at the translated
      click point and that `popup()` follows it, and that a repeat
      right-click then re-anchors (popdown before re-popup). Verify:
      the extended tests pass.
- [x] 2.2 Add a widget-level smoke test that builds the real window,
      attaches the popovers from `app.ui`, sends a synthetic secondary
      click (as in the exploration repro), and asserts the popover is
      visible with its on-screen origin near the click point; mark the
      test to skip when no display is available. Verify: the test passes
      under a display and is skipped (`-k`) without one.
- [x] 2.3 Run the app_window suite and confirm all affected tests pass
      with no new uncovered or partially covered lines in
      `src/scantpaper/app_window.py`. Verify: `pytest` on
      `test_app_window.py` and `python3 dev/check_test_coverage.py`.

## 3. Documentation and release gates

- [x] 3.1 Document the restored right-click context menus (shown anchored
      at the pointer) in the relevant user-visible section of README.md,
      and verify the rendered markdown follows the 80-column convention
      (`test_markdown_line_length`).
- [x] 3.2 Run the full quality gates and verify they are clean: `pytest`
      (99% coverage gate), `ruff format` then `ruff check`, and
      `ty check .` with no diagnostics.
