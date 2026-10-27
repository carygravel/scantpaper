# Tasks

## 1. Fix the Canvas hit-test transform

- [x] 1.1 Change `Canvas._hit_test` in `src/scantpaper/canvas.py` to derive
      the image point from `_scale_factors()` (`widget / sx -
      offset.x`), matching the renderer and the ImageView; verify the
      existing tests still pass with
      `pytest src/scantpaper/tests/test_7_canvas.py -k "hit_test or click"`.
- [x] 1.2 Add regression tests in `src/scantpaper/tests/test_7_canvas.py`
      that drive a widget click through `_button_pressed` with the display
      scale factor set to 2 and with the resolution ratio set to 0.5 (each
      at zoom 1, offset 0), asserting the intended word's edit callback is
      the one invoked; verify each test fails before 1.1 and passes after.
- [x] 1.3 Add an entry to the unreleased section of `changelog.md`
      describing the fixed click behaviour, and confirm the README
      "Layer editing" text still describes the interaction accurately
      (no rewrite expected).

## 2. Integration and quality gates

- [x] 2.1 Run the full suite with `pytest` and confirm every test passes
      under the configured coverage threshold, with no newly uncovered
      lines in the changed code.
- [x] 2.2 Run `ruff format`, `ruff check`, and `ty check .` and confirm no
      diagnostics, then run
      `openspec validate fix-canvas-hit-test-transform --strict`.

## Workflow follow-up

- Archive the change once the project's review requirements are satisfied.
