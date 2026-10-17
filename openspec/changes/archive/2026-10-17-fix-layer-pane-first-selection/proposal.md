# Proposal: fix-layer-pane-first-selection

## Why

On a page with no existing text layer, the Text layer and Annotation panes
cannot draw their first selection rectangle: the canvas refuses to start a
selection drag while no page extent is known, and the extent is only ever
learned from a loaded layer. With no rectangle the Add control never enables,
so the user cannot manually add a rectangle and text without first running
OCR on the page - violating the `layer-add-selection` requirement that a
selection can be drawn directly in a layer pane, and the `layer-editing`
requirement that a first slice can be created on a page with no layer.

## What Changes

- The layer pane learns the page's extent when a page is displayed, whether
  or not the page has a text layer or annotations, so a rectangle can be
  drawn before any OCR has run.
- The canvas already gates selection drags on a *known page extent* - not
  on layer content - so the gate code and the tests that lock it in stay
  unchanged; a new test covers drawing the first selection on a page whose
  extent is known but which has no layer.
- The fix is invariant to how "empty" is represented: it works whether the
  page's layer attribute is `None` (never OCR'd, blank OCR) or `"[]"`
  (Clear OCR), seeding the extent in both the create and clear paths.
- The `clear_text()` contract is unchanged (it still resets the size to
  `None`); the editor re-seeds the extent when a page is shown.
- No change to the Add control, the shared selection, or the `add()`
  no-layer path - those already work once a selection exists.
- Explicitly out of scope: unifying the `None` vs `"[]"` empty-layer
  sentinels (a separate cleanup).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `layer-add-selection`: add scenarios pinning that the first selection can
  be drawn in the Text layer pane and the Annotation pane on a page that has
  no existing layer - the current scenarios do not distinguish this case,
  which is how the bug shipped.
- `canvas-widget`: add a requirement that selection drawing is gated on a
  known page extent, not on a loaded text layer, so the gate's behaviour is
  specified rather than incidental. The existing `clear_text` requirement
  is unchanged.

## Impact

- **Code:** `src/scantpaper/session_mixins.py` (page load seeds the extent
  into both editors after the existing create/clear branch),
  `src/scantpaper/layer.py` (editor-level extent setter),
  `src/scantpaper/canvas.py` (page-extent setter, `hocr()` guard).
- **Tests:** `src/scantpaper/tests/test_layer.py` (add an integration test
  for the first selection on a layerless page),
  `src/scantpaper/tests/test_7_canvas.py` (the existing no-extent tests
  `test_canvas_click_without_pixbuf_does_not_draw` and
  `test_draw_scene_pixbuf_none` remain valid; add a drag test for the
  known-extent, no-layer state), `src/scantpaper/tests/test_session_mixins.py`
  (expect the new extent-seeding call).
- **Specs:** delta files for `layer-add-selection` and `canvas-widget`.
- **README:** the layer pane flow is already documented as working; add a
  note that it works without a prior OCR run.
- **User-visible:** the reported manual-OCR-workaround disappears; blank
  pages (OCR found nothing) become editable too.
