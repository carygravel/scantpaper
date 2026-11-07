# Design

## Context

See `proposal.md` for motivation and
`specs/keyboard-shortcut-scoping/spec.md` for the behavior contract.

The main window already has a bubble-phase `Gtk.EventControllerKey` attached in
`src/scantpaper/app_window.py`. It currently handles `Delete` only. Because the
controller is bubble-phase, it receives a key only after the focused widget has
had the chance to consume it; the layer editor's `Gtk.TextView` therefore keeps
keys it handles.

The conflicting shortcuts are registered on the application in
`src/scantpaper/app.py` with `set_accels_for_action()`. GTK4 treats these as
global accelerators and handles them in the capture phase, before the focused
widget. That ordering is the bug.

The page and view actions themselves are window actions (`win.*`) and are
already registered in `ApplicationWindow`. Menus and toolbars continue to
target those actions directly.

## Goals / Non-Goals

**Goals:**

- Let the focused text control keep the standard editing keys and printable
  `+` and `-`.
- Keep the page and view shortcuts working whenever focus is outside a text
  control.
- Keep the existing window actions, menus and toolbars as the single source of
  action behavior.
- Keep the handling testable without a live display.
- Preserve mouse-wheel zoom regardless of keyboard focus.

**Non-Goals:**

- Changing the page clipboard, page undo/redo, or layer commit semantics.
- Adding new keyboard zoom shortcuts such as `Ctrl+plus` or `Ctrl+minus`.
- Remapping universal shortcuts such as New, Open, Save, Print, or Quit.
- Providing user-configurable shortcut bindings.
- Changing Escape handling or other shortcuts outside the reported conflict.

## Decisions

### Remove the conflicting shortcuts from the application accelerator table

The following entries leave `_setup_accelerators()`: `cut`, `copy`, `paste`,
`select-all`, `undo`, `redo`, `zoom-in`, and `zoom-out`. Keeping any of them as
application accelerators would preserve the capture-phase interception and
defeat the fix.

Alternative considered: keep the accelerators and disable the actions while a
text control has focus. This still consumes the key before the text control and
requires fragile focus tracking, so it is rejected.

Alternative considered: let each action handler detect a focused text control
and forward the key to it. This duplicates widget editing behavior and cannot
forward a printable character from an action handler, so it is rejected.

### Handle the scoped keys in the existing bubble-phase window controller

The window key controller is extended to recognize the scoped keys. Because it
runs after the focused widget in the bubble phase, a text control naturally
keeps `+`, `-`, `Ctrl+X`, `Ctrl+C`, `Ctrl+V`, `Ctrl+A`, `Ctrl+Z` and
`Ctrl+Shift+Z`. As a safety net, the handler also returns without dispatching
when the current focus widget is a text input, so a text control that does not
consume a key cannot fall through to a page action.

Alternative considered: a new managed `Gtk.ShortcutController` on the window.
It is more declarative, but its interaction with widget class bindings is less
obvious and it complicates the existing Delete path. The bubble key controller
is already established in this codebase.

### Dispatch through the existing window actions

The handler activates the existing `win.*` actions rather than calling the
handlers directly. That keeps enabled state, menu synchronization, and existing
behavior in one place. For example, an insensitive `win.zoom-in` action stays
inert exactly as it does from the menu.

### Match the unshifted editing forms and the shifted redo form

The handler normalizes the key value to lower case and uses the modifier state
to distinguish the variants:

- `Ctrl+X`, `Ctrl+C`, `Ctrl+V`, `Ctrl+A`: control held, no shift, alt, or
  super.
- `Ctrl+Z`: control held, no shift.
- `Ctrl+Shift+Z`: control and shift held; redo.
- `+` and `-`: no control, alt, or super. Shift is ignored because some
  keyboard layouts need Shift to produce `+`.
- Numpad `+` and `-` are matched as the same printable zoom keys outside text
  controls, so the keyboard behavior is consistent across the main and numeric
  keypads.
- Plain `Delete`: no shift, control, alt, or super. Modified Delete presses are
  left alone.

Alternative considered: match only the exact accelerator syntax strings. That
would not express the focus-sensitive distinction and would not handle the
keyboard-layout variation around `+`.

### Keep bare `+` and `-` as the keyboard zoom keys

Option A is preserved: bare `+` and `-` zoom whenever focus is outside a text
control. No new `Ctrl+plus`/`Ctrl+minus` accelerator is added. The mouse wheel
continues to zoom over the image view regardless of focus.

Alternative considered: move zoom to `Ctrl+plus`/`Ctrl+minus`. This would let
zoom work while typing but changes a documented shortcut and adds layout
variation. It is not part of this change.

Alternative considered: remove keyboard zoom entirely. The wheel remains
available, but keyboard-only users would lose zoom, so this is rejected.

### Accept the menu accelerator-hint trade-off

GTK's in-window menu reads shortcut hints from the application accelerator
table. Removing these entries may stop the Edit and View menus from displaying
the hints for the moved actions. The actions remain present and usable, and the
README documents the shortcuts. If implementation shows the hints are valuable
enough to preserve, the fallback is a window-managed shortcut controller, but
that is not required for the behavior contract.

## Risks / Trade-offs

- [Focus remains in a text control after the user clicks the image view] -> The
  mouse wheel still zooms over the image, and clicking the page list or another
  non-text control restores the keyboard zoom context. The README states the
  scoping.
- [A text control that does not consume a key could fall through] -> The
  handler explicitly checks for a focused text input before dispatching.
- [A custom text widget is not recognized by the focus guard] -> The guard
  covers `Gtk.TextView` and `Gtk.Editable`; the bubble phase remains the
  primary protection, so an unrecognized widget that consumes its keys is
  still safe.
- [Keyboard layouts differ around `+`, `-` and `Ctrl+Shift+Z`] -> Normalize
  the key value and test modifier combinations, including numpad keys.
- [Page actions become unreachable while typing] -> They remain in the menus
  and toolbars; the spec requires them to stay available.
- [Shortcut hints may disappear from the menus] -> Accept the cosmetic change
  or revisit with a managed shortcut controller if it proves important.

## Migration Plan

No data migration is required. The change is stateless: reverting the
accelerator table, the key-handler changes, the tests, and the README restores
the previous behavior.
