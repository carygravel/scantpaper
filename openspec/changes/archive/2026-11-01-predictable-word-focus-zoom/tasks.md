# Tasks

## 1. Focus zoom maths in ImageView

- [x] 1.1 Add tests to `src/scantpaper/tests/test_imageview.py` for a focus-zoom
  helper: the same text height for short and long boxes at a fixed line height,
  the level multiplier, the fit margin in a narrow allocation, clamping, and
  `zoom_is_fit` left false. Verify the new tests fail for the intended reason
  with `pytest --no-cov src/scantpaper/tests/test_imageview.py`.
- [x] 1.2 Add `FOCUS_TEXT_HEIGHT`, `FOCUS_MARGIN`, `DEFAULT_FOCUS_ZOOM`,
  `MIN_FOCUS_ZOOM`, `MAX_FOCUS_ZOOM` and `FOCUS_ZOOM_STEP` to
  `src/scantpaper/const.py`. Verify they are importable and
  `ruff check src/scantpaper/const.py` is clean.
- [x] 1.3 Factor the fit calculation out of `ImageView.zoom_to_box` and
  implement the focus-zoom helper using the constants. Verify
  `pytest --no-cov src/scantpaper/tests/test_imageview.py` passes.

## 2. Line-derived text height

- [x] 2.1 Add tests for a `focus_text_height(bbox)` helper: the line's `x_size`
  is preferred, a line box is used at 0/180 (height) and 90/270 (width), a
  missing `x_size` falls back to the box, and a slice with no line ancestor
  falls back to its own `x_size` then box. Verify the tests fail with
  `pytest --no-cov src/scantpaper/tests/test_layer.py`.
- [x] 2.2 Implement the helper in `src/scantpaper/layer.py`, walking to the
  nearest line ancestor and using `Canvas.accumulated_textangle`. Verify
  `pytest --no-cov src/scantpaper/tests/test_layer.py` passes.

## 3. Route every focus path through the new zoom

- [x] 3.1 Update the focus tests in `src/scantpaper/tests/test_layer.py` so
  `edit` is expected to request focus zoom with the derived text height and the
  current level, and so click, first/previous/next/last, accept/delete advance
  and add/duplicate all use the same path. Verify the tests fail.
- [x] 3.2 Implement `_apply_focus_zoom`, call it from `edit`, and give
  `LayerEditor` a `get_focus_zoom` callable defaulting to
  `DEFAULT_FOCUS_ZOOM`. Verify `pytest --no-cov
  src/scantpaper/tests/test_layer.py` passes.
- [x] 3.3 Remove `ZOOM_CONTEXT_FACTOR` from `src/scantpaper/const.py` and its
  last use. Verify `grep -R ZOOM_CONTEXT_FACTOR src` prints nothing and
  `pytest --no-cov src/scantpaper/tests/test_layer.py` passes.

## 4. In-context focus control

- [x] 4.1 Add tests to `src/scantpaper/tests/test_text_layer_control.py` for a
  focus control enabled by a feature flag: the initial percentage, emission on
  a scale change, reset to 100, a programmatic `set_focus_zoom` that does not
  emit, and the tooltip. Verify the tests fail.
- [x] 4.2 Implement the `Gtk.MenuButton` with its popover, 50-200 scale, reset
  button and `focus-zoom-changed` signal in `LayerControls`, and enable it for
  both editors. Verify
  `pytest --no-cov src/scantpaper/tests/test_text_layer_control.py` passes.
- [x] 4.3 Regenerate the translation template with
  `PYTHONPATH=src python3 dev/generate_pot.py`, then verify the new strings are
  in `po/scantpaper.pot` with `git diff` and that
  `PYTHONPATH=src python3 dev/check_po.py` passes. Do not add a non-fuzzy
  translation.

## 5. Persistence, wiring and documentation

- [x] 5.1 Add `"focus zoom": DEFAULT_FOCUS_ZOOM` to `config.DEFAULTS` and tests
  in `src/scantpaper/tests/test_8_config.py` for the default and a config
  round-trip. Verify `pytest --no-cov src/scantpaper/tests/test_8_config.py`
  passes.
- [x] 5.2 Pass `get_focus_zoom` and `set_focus_zoom` closures from
  `app_window` into both editors. The setter clamps, stores the value in
  `settings`, and updates both control bars with their change handlers blocked.
  Verify the sync and persistence tests with
  `pytest --no-cov src/scantpaper/tests/test_layer.py
  src/scantpaper/tests/test_text_layer_control.py`.
- [x] 5.3 Re-apply the focus zoom to the current bbox when the level changes,
  without repeating the text-buffer work, and cover it with a test. Verify
  `pytest --no-cov src/scantpaper/tests/test_layer.py` passes.
- [x] 5.4 Describe the focus zoom and its control in the layer-editing section
  of `README.md`. Verify the wording matches the implemented control by reading
  the section and checking `git diff README.md`.

## 6. Integration checks

- [x] 6.1 Run the full suite with `pytest`; verify it passes and the coverage
  gate is at least 99%.
- [x] 6.2 Run `ruff format --check .`, `ruff check .` and `ty check .`; verify
  all are clean.
- [x] 6.3 Run `python3 dev/check_test_coverage.py`; verify there are no new
  unexecuted or partially covered lines beyond the recorded baseline.
- [x] 6.4 Smoke test in the GUI: OCR a page, edit the text layer sorted by
  confidence, and step through words. Verify short and long words render at the
  same text size, a long word stays visible in a narrow split pane, the slider
  re-zooms live, reset works, the level survives a restart, and the annotation
  layer uses the same level.
- [x] 6.5 Run `openspec validate predictable-word-focus-zoom --type change
  --strict --no-interactive` and
  `openspec validate --specs --strict --no-interactive`; verify both pass.

## Workflow follow-up

- Archive the change after review and verify the archived
  `slice-focus-zoom` spec contains the new requirements.
