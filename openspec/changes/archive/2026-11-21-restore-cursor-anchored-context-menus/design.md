# Design

## Context

See proposal.md — Why. The GTK3→4 migration (commit `e4e067a2`) replaced
`GtkMenu.popup_at_pointer(event)` with a `GtkPopover` that is parented to the
whole application window in `_connect_popover_signals`
(`src/scantpaper/app_window.py:896-897`) and shown with a bare `popup()`
in `_handle_clicks` (`app_window.py:917,920`). With no pointing target, a
`GtkPopover.popup()` anchors to its parent's allocation — the whole window —
so the menu renders at the window's top-left corner, off the cursor and
often clipped. Reproduced on GTK 4.14.5: with the click at (150,100), the
derived popover surface landed at the window's top-left, bleeding off-screen
(the repro is noted in tasks for reuse).

The two affected surfaces and their menus: image view → `detail_popup`,
thumbnail list → `thumb_popup`. Both live in `src/scantpaper/app.ui` and are
already wired (`_connect_popover_signals`), so the menu *contents and signal
wiring are not part of this change* — only the anchoring.

## Goals / Non-Goals

**Goals**

- Show both context menus anchored at the right-click pointer on every
  supported GTK4 version.
- Keep the existing parent/child setup and `GtkPopover` model; no new
  widget class or menu framework.

**Non-Goals**

- Adding, removing, or reordering menu items, or changing popover contents.
- Changing how the inner tool-selection toggle buttons drive the
  `win.tooltype` action.
- Fixing the (separate, pre-existing) event-swallowing or double-popover
  concerns — out of scope unless live testing exposes them.
- Keyboard-activated context menus (e.g. the Shift+F10 menu key).

## Decisions

### D1. Anchor via `Gtk.Popover.set_pointing_to()` + `popup()`

In `_handle_clicks`, translate the gesture point from the clicked widget
into the window (the popover's parent) coordinate space and pass it as the
pointing rectangle:

```
- (x, y) from the gesture is in the clicked widget's coordinates.
- pt = widget.compute_point(window, GdkPoint(round(x), round(y)))
- rect = Gdk.Rectangle(); rect.x, rect.y = int(pt.x), int(pt.y);
  rect.width = rect.height = 1
- popover.set_pointing_to(rect); popover.popup()
- if the popover is already visible, popdown() before re-showing so a
  second right-click re-anchors cleanly
```

`gtk_popover_set_pointing_to` has existed since GTK 4.0, so this works
across the supported range (jammy-era GTK4 through current). GTK's popover
positioning then automatically flips/clamps placement to the screen edge,
satisfying the "stays on-screen" requirement without manual math.

Alternative considered: reparent each popover to the *clicked widget* at
click time (`set_parent(image_view)` then `popup()`). Simpler to read, but
it anchors to the widget's full allocation rather than the exact cursor and
re-parenting on every click risks mapping flicker; also
`gesture.get_widget()` is not exposed to "where" the click happened.
Rejected.

Alternative considered: `gtk_popover_present()` instead of `popup()`. It
uses the same parent-derived anchoring, so it does not fix the cursor
placement. Rejected.

Alternative considered: re-introducing `GtkMenu`/`GtkPopoverMenu` and using
a `GtkGesture`-triggered `menu.popup_at_pointer()`-equivalent. GTK4 has no
`popup_at_pointer`; `GtkPopover` is the supported component. Rejected as
unnecessary churn.

### D2. Keep `set_parent(window)` at startup; do not move parenting

Both popovers stay parented to the window in `_connect_popover_signals`,
unchanged. `set_pointing_to` interprets its rectangle in the parent's
coordinate space; pointing into the window is correct and requires only the
one `compute_point` translation.

### D3. Response to pointer-relative sensitivity

No changes. `detail_popup.set_sensitive()` already toggles on selection
(`app_window.py:1197`); the spec's "menu shown, insensitive items" scenario
is satisfied by existing behaviour. The thumb menu's "Page range = selected"
assignment also stays as-is.

## Risks / Trade-offs

- [`compute_point` returns window coordinates only meaningful once the
  window is allocated; a click before first allocation could mis-translate]
  → Right-click only arrives on a mapped, allocated widget, so this cannot
  happen in practice; still, fall back to (0, 0) if `compute_point`
  raises or returns None.
- [Multi-GTK-version variance in popover flipping at screen edges] → The
  spec requires the menu to stay on-screen; GTK handles flip/clamp for
  toplevel popovers on all 4.x versions. Verified interactively on the
  build in CI if position is still wrong on an older release.
- [The existing unit test mocks the popover, so pure unit tests cannot
  prove screen position] → Extend the unit test to assert `set_pointing_to`
  is called with the translated point, and add a widget-level smoke test
  (real window + synthetic right-click, as in the exploration repro) that
  asserts the popover surface is visible and its origin is near the click
  point; keep that test skipped when no display is available.

## Migration Plan

Single in-repo change; no data or service migration. Rollback is a revert
of the commit (the menus revert to window-corner anchoring, i.e. the
current state).

## Open Questions

- None that would change the specs or approach. (Whether the menu-key
  (Shift+F10) should open the same menus is a possible future enhancement,
  explicitly out of scope here.)
