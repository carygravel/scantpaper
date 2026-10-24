# Proposal

## Why

Since the GTK3 to GTK4 port, neither the selection rectangle in the image
view nor the one in the text-layer canvas is visible. Both widgets paint
their selection with the `rubberband` CSS class, but GTK4's default theme
only styles `rubberband` as a *node* that is a child of selection widgets
(`flowbox > rubberband`, `treeview.view > rubberband`, `gridview >
rubberband`, ...). It ships no `.rubberband` *class* rule, so
`render_background()`/`render_frame()` paint nothing on a DrawingArea. GTK3
themes led their selector with `.rubberband`, which is why the migration
broke exactly these two rectangles. The fix is a small app-supplied CSS
rule, which also makes the selection follow the active theme and honour a
user's `~/.config/gtk-4.0/gtk.css` override.

## What Changes

- Ship an application-level `Gtk.CssProvider` that defines the
  `.rubberband` class (translucent background and border), installed at
  `GTK_STYLE_PROVIDER_PRIORITY_APPLICATION` alongside the existing
  thumbnail stylesheet, so a user's gtk.css override still wins.
- Load the rule with `CssProvider.load_from_data()`, the GTK 4.6 floor
  method (`load_from_string()` does not exist on jammy).
- Keep both draw paths unchanged: the ImageView (`imageview.py`) and the
  Canvas (`canvas.py`) already add the `rubberband` class and call
  `render_background()`/`render_frame()`; the CSS rule is what makes them
  paint.
- The selection rectangle therefore becomes visible in the image view and
  in the text-layer canvas at every supported GTK version (4.6, 4.14,
  4.24), and follows the active theme's colours.
- Add pixel-level regression tests for both widgets asserting the
  selection actually paints. The existing tests only assert that the
  render calls happen, which is why this breakage passed CI.

## Capabilities

### New Capabilities

None — this change extends two existing selection capabilities; no new
capability boundary is warranted.

### Modified Capabilities

- `canvas-widget`: the canvas selection rectangle SHALL be painted via the
  application's `.rubberband` class rule so it is visible and themeable.
  The current requirements assert alignment and that a rubber-band follows
  the pointer, but not that it is visibly painted.
- `layer-add-selection`: the selection rectangle shown in the image view
  SHALL be painted with the same `.rubberband` style, so the single shared
  selection is visibly rendered and themeable in both panes.

## Impact

- `imageview.py` and `canvas.py`: no change to the selection draw paths.
- New CSS rule, hosted beside `_attach_thumbnail_css()` in `app_window.py`
  (or a shared helper), installed once per display.
- Tests: pixel-assertion coverage in `tests/test_imageview.py` and
  `tests/test_7_canvas.py`; CI runs on the jammy floor, where the rule must
  load through `load_from_data()`.
- No new dependencies; no data-model or saved-format changes.
- README FAQ ("How can I change the colour of the selection box") stays
  accurate because a user rule overrides the shipped default at higher CSS
  priority; the wording may note that a default is now shipped.
