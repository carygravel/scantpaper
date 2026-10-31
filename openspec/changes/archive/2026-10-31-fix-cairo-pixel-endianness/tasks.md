# Tasks

## 1. Shared decoder and regression test

- [x] 1.1 Add `src/scantpaper/tests/pixel_helpers.py` with
  `argb32_rgb(raw, offset, byteorder=sys.byteorder)` returning `(r, g, b)` and
  a docstring stating that Cairo's `ARGB32` layout is native-endian. Verify
  `ruff check` and `ty check` report no issues for the new module.
- [x] 1.2 Add a parameterised test in
  `src/scantpaper/tests/test_pixel_helpers.py` covering little-endian and
  big-endian red and green sequences. Verify with
  `pytest src/scantpaper/tests/test_pixel_helpers.py`, including the big-endian
  cases that a hard-coded little-endian decoder would fail.

## 2. Image-view reader

- [x] 2.1 Replace the little-endian unpacking in `_SurfaceReader.__init__` with
  `argb32_rgb(raw, offset, sys.byteorder)` while keeping the existing RGB
  buffer interface, and update the class docstring. Verify:

  ```sh
  IMG=src/scantpaper/tests/test_imageview.py
  pytest "$IMG" -k "test_transparency or test_filter"
  pytest "$IMG" -k "test_imageview_selection_is_themeable"
  ```

## 3. Canvas reader and assertion

- [x] 3.1 Change `_canvas_pixel` to return a decoded `(r, g, b)` tuple, update
  `_canvas_selection_center_pixel` and its docstring, and change the themeable
  assertion to `(255, 0, 0)`. Verify:

  ```sh
  CANVAS=src/scantpaper/tests/test_7_canvas.py
  pytest "$CANVAS" -k "selection_paints_with_rule"
  pytest "$CANVAS" -k "selection_is_themeable"
  ```

## 4. Integration checks

- [x] 4.1 Search `src/scantpaper/tests` for `get_data()` and confirm every
  Cairo pixel read goes through `argb32_rgb`; verify with
  `grep -rn "get_data" src/scantpaper/tests`.
- [x] 4.2 Run `pytest` and confirm all tests pass and the coverage gate (99%) is
  met.
- [x] 4.3 Run `ruff check .`, `ruff format --check .` and `ty check .` and
  confirm there are no diagnostics.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Include the test fix in the next release so the Debian autopkgtest on s390x
  picks it up.
