## Context

See proposal.md - Why. The menu structure is a single `GMenu` model declared
in `app.ui` (`<menu id="menubar">`), whose items reference the window's
`win.*` actions. Accelerators are registered in `app.py`
(`Gtk.Application.set_accels_for_action`) because GTK4 does not honour
`accel` attributes in a `GMenuModel`. `app_window._populate_main_window()`
loads `main_vbox` from `app.ui` and sets it as the window child; the toolbar
is its first child today.

## Goals / Non-Goals

**Goals:**
- Menus visible in the main window on every desktop.
- No change to the menu model's items/actions or to the registered
  accelerators.
- One definition of the menu structure.

**Non-Goals:**
- Replacing the toolbar or moving actions into a header bar.
- Redesigning the menu contents (items are ported 1:1 from GTK3).
- Desktop-shell/global-menu integration.

## Decisions

**D1. Use `Gtk.PopoverMenuBar`, not `Gtk.MenuButton` or `Gtk.HeaderBar`.**
`PopoverMenuBar` is GTK4's in-window menubar: a horizontal strip of titles
whose items open as popovers. It consumes the existing model with submenus
as-is, works on every desktop, and needs no restructure of the window. A
hamburger `Gtk.MenuButton` would hide every menu one level deeper and remove
the discoverable top-level titles; a `Gtk.HeaderBar` would restructure the
window and move the toolbar. `PopoverMenuBar` exists since GTK 4.0, so the
jammy floor is unaffected.

**D2. Define the menubar in `app.ui`, not in Python.** The
`Gtk.PopoverMenuBar` is added as the first child of `main_vbox` with its
`menu-model` property containing the existing `<menu>` block. This keeps the
model declarative and in one place, and avoids a Python construction path
that the `app_window` tests would have to mock around (their `Gtk.Builder`
is a mock, so `get_object("menubar")` returns a mock that
`PopoverMenuBar.new_from_model()` cannot consume).

**D3. Remove `Gtk.Application.set_menubar()`.** Keeping it would mean either
a second copy of the model or a builder reference whose only consumer is a
call that no current desktop renders; removing it leaves a single definition
and avoids duplicate menus on any desktop that does render the exported
model. Accelerators continue to be registered on `win.*` actions
independently of the menubar, so shortcuts are unaffected.

**D4. Keep the placement at the top of the window content, above the
toolbar**, matching the GTK3 layout (menubar, then toolbar, then panes). The
menubar is presentation only; the panes and their saved divider positions are
untouched.

## Risks / Trade-offs

- [PopoverMenuBar opens menus on click, not on hover like a GTK3 menubar] →
  Accepted: it is the GTK4-native behaviour; top-level titles remain visible
  and keyboard navigation (F10, arrows) works.
- [Moving the `<menu>` block into the `GtkPopoverMenuBar` property could
  break the `Gtk.Builder` load if the XML is malformed] → Mitigated by a test
  that loads the real `app.ui` and asserts the bar and its model.
- [Some stateful actions (e.g. view mode, edit mode) rendered as toggles may
  look different in a popover] → Accepted for this change; action semantics
  are unchanged and enable/disable state still tracks the actions.
- [Removing `set_menubar()` changes behaviour on desktops that render the
  exported model (they lose the shell menu but gain the in-window one)] →
  Accepted: the in-window menu is present everywhere and the action set is
  identical.

## Migration Plan

Single change: move the model in `app.ui`, delete the `set_menubar()` call,
add the UI/model tests. Rollback is reverting the commit; no data or config
migration is involved.
