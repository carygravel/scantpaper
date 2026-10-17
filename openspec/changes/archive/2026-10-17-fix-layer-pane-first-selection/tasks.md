# Tasks: fix-layer-pane-first-selection

## 1. Canvas: page extent independent of layer content

- [x] 1.1 Add tests in `tests/test_7_canvas.py`: `set_page_extent()`
  records the extent and queues a draw; with a known extent and an empty
  root, press/motion/release emits `selection-drawn` with the drag
  rectangle; with no extent the existing no-draw behaviour still holds
  (keep `test_draw_scene_pixbuf_none` and
  `test_canvas_click_without_pixbuf_does_not_draw` unchanged)
- [x] 1.2 Add a test that `hocr()` returns `""` when the extent is known
  but the root has no children (previously an `IndexError` path)
- [x] 1.3 Implement `Canvas.set_page_extent(width, height)` and harden
  `hocr()`'s guard to `no extent or no children` (design D1, D3)

## 2. Editor and page-load wiring

- [x] 2.1 Add a test for `LayerEditor.set_extent(width, height, offset)`:
  it sets the canvas extent and applies the offset
- [x] 2.2 Add tests in `tests/test_session_mixins.py`: after
  `_on_page_loaded`, both editors receive `set_extent` with
  `page.get_size()` and the view offset - for pages with a layer, without
  a layer (`None`), and with an empty sentinel (`"[]"`); update existing
  mock expectations as needed (design D4)
- [x] 2.3 Implement `LayerEditor.set_extent` and call it for both editors
  in `_on_page_loaded` after the existing create/clear branch (design D1)

## 3. Regression test for the reported bug

- [x] 3.1 Add an integration test in `tests/test_layer.py` that keeps the
  real canvas (no `Mock` replacement as in `test_add_creates_new_layer`):
  a page with no text layer, simulate a drag in the Text layer pane ->
  `selection-drawn` fires -> Add control becomes enabled -> `add()`
  creates the layer with the new slice

## 4. Documentation and quality gates

- [x] 4.1 README: note in the layer-pane paragraph that drawing a
  rectangle there works on pages that have not been OCRed
- [x] 4.2 Run `ruff format`, `ruff check`, and `ty check .` clean
- [x] 4.3 Run `pytest`: all green, no drop in coverage (new branches
  covered, including the `hocr()` empty-root guard and the three
  `_on_page_loaded` variants)
- [x] 4.4 Run `openspec validate --change fix-layer-pane-first-selection`
