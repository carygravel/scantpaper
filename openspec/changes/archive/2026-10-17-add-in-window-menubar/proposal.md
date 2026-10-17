## Why

After the GTK4 port, no menus appear in the main window. GTK4's
`Gtk.Application.set_menubar()` does not draw an in-window menubar: it only
exports the menu model for the desktop shell to render, and GNOME (and most
other desktops) no longer display it. The actions remain reachable through
the toolbar and keyboard shortcuts, but the menu structure — the primary way
users discover the application's functionality — is invisible.

## What Changes

- Replace the shell-exported `Gtk.Application.set_menubar()` menubar with an
  in-window `Gtk.PopoverMenuBar` built from the same `GMenu` model, placed at
  the top of the main window (above the toolbar).
- The menu model itself and every `win.*`/`app.*` action stay unchanged, so
  no accelerators, mnemonics or action logic change.
- Keep a single definition of the menu model in `app.ui`.

## Capabilities

### New Capabilities

- `main-menu`: the main window presents the application's menu structure
  in-window, on every desktop, so all actions are discoverable without
  relying on desktop-shell integration.

### Modified Capabilities

None.

## Impact

- `src/scantpaper/app.ui`: the `menubar` menu model moves inside a
  `GtkPopoverMenuBar` that is the first child of `main_vbox`.
- `src/scantpaper/app_window.py`: the `set_menubar()` call is removed.
- Tests: a new test loads the real `app.ui` and asserts the in-window menubar
  model; tests that patched `set_menubar` are updated.
- No new dependencies; `Gtk.PopoverMenuBar` exists since GTK 4.0, so the
  jammy floor is unaffected.
