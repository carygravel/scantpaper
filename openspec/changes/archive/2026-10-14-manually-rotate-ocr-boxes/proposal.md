## Why

Books often contain index pages whose text is rotated 90° (read bottom-to-top).
Tesseract does detect and display such boxes rotated, but frequently the glyph
content it recognises is wrong, so the user wants to author the correct text by
hand. Today a user can draw a box and type text, but there is no way to make a
new or existing box hold rotated text, so vertical text cannot be corrected.

## What Changes

- Add rotate-clockwise and rotate-anticlockwise controls to the text-layer
  editing bar.
- Rotating a focused text slice sets its `textangle` to 90 or 270, so the text
  is drawn rotated (bottom-to-top or top-to-bottom) on the canvas.
- The rotation is persisted in the page's text layer and embedded in saved
  output, following the same `textangle` path Tesseract's own vertical boxes
  already use.
- New slices created while a rotation is set inherit the current rotation so a
  user can author a run of vertical text.

## Capabilities

### New Capabilities

None. This change extends behaviour of the existing text-layer editor rather
than introducing a new capability.

### Modified Capabilities

- `layer-editing`: adds a requirement that a focused text slice can be rotated
  clockwise or anticlockwise by 90°, that the rotation is drawn on the page,
  and that it is persisted in the page's text layer and saved output.

## Impact

- `src/scantpaper/layer.py`: add rotate controls to `LayerControls` and wire
  them in `LayerEditor` to set the focused slice's rotation.
- `src/scantpaper/canvas.py`: carry a `textangle` through `add_box` /
  `update_word` so a newly added or corrected slice keeps/acquires the intended
  rotation; drawing already honours `textangle`.
- `src/scantpaper/bboxtree.py` and `page.py`: unchanged - `textangle` already
  round-trips through the hOCR serialisation and save path.
- Tests: extend `src/scantpaper/tests/test_7_canvas.py`, `test_layer.py`, and
  `test_text_layer_control.py` to cover rotation of a slice.
