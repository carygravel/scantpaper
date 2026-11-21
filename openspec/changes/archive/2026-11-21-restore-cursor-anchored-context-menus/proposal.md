# Proposal

## Why

After the GTK3→4 migration, the right-click context menus on the image view
and the thumbnail list are no longer anchored to the pointer. They were
ported from `GtkMenu.popup_at_pointer(event)` to a `GtkPopover` parented to
the whole window and shown with a bare `popup()`, so the menu pops at the
window's top-left corner (often partially clipped off-screen) instead of
under the cursor. Users perceive this as the context menu having
disappeared.

## What Changes

- Right-clicking the **image view** again shows the page context menu
  (tool selection, zoom, rotate, crop, cut/copy/paste, delete, properties)
  at the pointer position, on every GTK4 version.
- Right-clicking the **thumbnail list** again shows the selection/page
  context menu (save, email, print, select all/odd/even/invert, rotate,
  crop, cut/copy/paste, delete, clear OCR, properties) at the pointer
  position.
- Both menus are anchored to the click point and stay on-screen; the
  current window-corner anchoring is removed.

## Capabilities

### New Capabilities
- `context-menus`: Right-click (secondary-button) context menus on the main
  window's interactive surfaces — the image view and the thumbnail list —
  shown anchored at the pointer. Owns the durable behavior: which surfaces
  have a context menu, that it appears at the cursor, and that it stays on
  screen without clipping.

### Modified Capabilities

None. The existing `image-view-tools`, `thumbnail-display`, and `main-menu`
specs cover button-press drag behaviour, thumbnail painting, and the
in-window menu bar respectively; none describes these popovers.

## Impact

- **Code**: `src/scantpaper/app_window.py` — `_handle_clicks`,
  `_add_secondary_click_controller`, and `_connect_popover_signals`
  (popover parenting). `src/scantpaper/app.ui` (popover
  `detail_popup`/`thumb_popup`) likely unchanged.
- **Tests**: `src/scantpaper/tests/test_app_window.py` `test_handle_clicks`
  only asserts `.popup()` is called, not where the popover renders; it will
  be extended to assert pointer anchoring.
- **Behaviour**: purely a restore of GTK3-era left/right-click interaction;
  no dependencies or data-model changes.
