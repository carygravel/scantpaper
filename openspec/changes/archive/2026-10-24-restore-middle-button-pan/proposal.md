# Proposal

## Why

Since the GTK3 to GTK4 port, middle-click dragging no longer pans the image
view or the OCR canvas. GTK4 replaced the `button-press-event` /
`button-release-event` signals (which delivered every mouse button) with a
`Gtk.GestureClick`, whose default `button` property is 1 — it reports only
the *primary* button. Middle-button presses are silently dropped, so every
`Gdk.BUTTON_MIDDLE` branch in the migrated handlers is now unreachable: the
`SelectorDragger` ("combined move/select") tool never switches to its
`Dragger` on a middle press, and the Canvas never starts a middle-drag pan.
This violates the existing `canvas-widget` requirement "Canvas supports
middle-click drag panning" and is a visible regression from GTK3.

## What Changes

- Point the single click gesture on both widgets at *any* button —
  `Gtk.GestureClick(button=0)` — so presses of every button reach the tool
  handlers again, exactly as GTK3's button signals did. The handlers
  already decide per-button what to do (`Gdk.BUTTON_MIDDLE` pans; the
  secondary button returns `False` and stays out of the way of the
  separate context-menu gesture).
- Middle-click-drag pans the OCR canvas again, matching the existing
  `canvas-widget` requirement.
- Middle-click-drag pans the image view when the default combined
  move/select tool (`selectordragger`) is active, selecting with the
  primary button and dragging with the middle button. The dedicated
  dragger tool continues to pan with the primary button.
- Left-button selection in the image view is unaffected, and secondary
  button context menus (delivered by the app's own
  `Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)` in `app_window.py`)
  are unaffected.
- Add regression tests asserting the click gesture of each widget is
  configured to receive non-primary buttons. The current unit tests mock
  the gesture (`_gesture()`), so they pass while the real GTK4 gesture
  never fires for a middle press — this is why the breakage went
  unnoticed.

## Capabilities

### New Capabilities

- `image-view-tools`: the image view's interaction tools and their
  button routing — `Selector` (primary selects), the panning `Dragger`,
  and the default combined `SelectorDragger` (primary selects with a
  rubber-band, middle drags/pans). This contract currently lives only in
  code comments ("Select with LMB, drag with MMB") and has no spec.

### Modified Capabilities

None. The Canvas already specifies "Canvas supports middle-click drag
panning"; this change restores conformance with that wording, so no
requirement text changes there.

## Impact

- `src/scantpaper/canvas.py` (the `Gtk.GestureClick()` created in
  `Canvas.__init__`) and `src/scantpaper/imageview.py` (the
  `Gtk.GestureClick()` created in `ImageView.__init__`): pass `button=0`
  to the existing gesture; no handler-line changes.
- Tests: extend `tests/test_7_canvas.py` and `tests/test_imageview.py`
  with a gesture-configuration assertion (the widget's click controller
  SHALL listen to any button). Optionally add a hatched event-injection
  check that an injected middle-button press reaches
  `SelectorDragger`'s `Dragger` and pans.
- No new dependencies; no config, data-model, or saved-format changes.
- Verified experimentally on GTK 4.24.1 by injecting real X11 button
  events (libXtst) through both stock and fixed widgets. The documented
  default is GTK-version-dependent, which is exactly why the fix sets the
  button explicitly rather than relying on a default.
