# Tasks

## 1. Keep the page-range frame at its natural height

- [x] 1.1 Remove the radio buttons' `set_vexpand(True)` call in
  `src/scantpaper/pagerange.py`, then run
  `python3 -m pytest src/scantpaper/tests/test_6_pagerange.py -q` and verify
  the existing page-range tests pass.
- [x] 1.2 Add a test asserting that a new `PageRange` does not compute as
  vertically expanding (for example
  `prg.compute_expand(Gtk.Orientation.VERTICAL) is False`) and that its
  buttons do not request expansion; verify the new test fails before 1.1 and
  passes after it.

## 2. Expose the advanced OCR expander

- [x] 2.1 Add a public read-only `advanced_expander` property to
  `OCRControls` that returns the `Gtk.Expander` or `None` when the Tesseract
  controls were not created; verify `ty check .` accepts the property and
  the module imports.
- [x] 2.2 Add tests in `src/scantpaper/tests/test_postprocess_controls.py`
  asserting that a tesseract `OCRControls` returns its expander and a
  non-tesseract one returns `None`; verify both tests pass with
  `python3 -m pytest src/scantpaper/tests/test_postprocess_controls.py -q`.

## 3. Restore the OCR dialog height on collapse

- [x] 3.1 In `ToolsMenuMixins.ocr_dialog()`, connect the advanced expander's
  `notify::expanded` signal, record `get_surface().get_height()` when it
  expands, and call `set_default_size(current_width, recorded_height)` when
  it collapses; verify with a mocked-dialog test that expanding records the
  height and collapsing requests that height with the current width.
- [x] 3.2 Cover the guards: a missing surface skips resizing, and a
  non-tesseract `OCRControls` (no expander) neither connects nor raises;
  verify both cases with tests in
  `src/scantpaper/tests/test_tool_menu_mixins.py`.
- [x] 3.3 Add an entry under `4.0.2 (unreleased)` in `changelog.md`
  describing the restored dialog height and the page-range frame no longer
  stretching; verify the text wraps at 80 characters and `README.md` needs no
  change because the OCR options themselves are unchanged.

## 4. Integration verification

- [x] 4.1 Add a window-level test that presents a real dialog containing a
  page-range frame and an expander, expands and collapses the expander while
  running the main loop, and asserts the surface height returns to its
  pre-expand value and the frame height stays natural; verify it passes under
  the suite's Xvfb setup.
- [x] 4.2 Run `ruff format`, `ruff check`, `ty check .`, and the full
  `pytest` suite; verify all pass, coverage does not decrease, and the new
  lines are covered.

## Workflow follow-up

- Archive the change after implementation and review.
- Verify the archived `dialog-layout` spec contains the new requirements.
