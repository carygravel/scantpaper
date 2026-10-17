## 1. Menubar in the UI definition

- [x] 1.1 In `app.ui`, move the `<menu id="menubar">` block into the
      `menu-model` property of a new `GtkPopoverMenuBar` with id `menubar`,
      as the first child of `main_vbox` (above `toolbar`).
- [x] 1.2 In `app_window.py`, remove the
      `self.get_application().set_menubar(...)` call.
- [x] 1.3 Remove the now-stale `set_menubar` patches from the tests that
      added them to suppress that call.

## 2. Tests

- [x] 2.1 Add a test that loads the real `app.ui` with `Gtk.Builder` and
      asserts `builder.get_object("menubar")` is a `GtkPopoverMenuBar` that
      is the first child of `main_vbox` (before `toolbar`).
- [x] 2.2 Assert the bar's model exposes the five top-level menus (File,
      Edit, View, Tools, Help) and that a representative item still refers
      to its `win.*` action (e.g. File → New is `win.new`).
- [x] 2.3 Assert every action referenced by the menu model is registered
      (`win.*` on the window, `app.*` on the application), so the model
      cannot drift from the action registration.

## 3. Documentation and gates

- [x] 3.1 Confirm README needs no change (menus are already documented as
      part of the UI); update if any statement about menus is now wrong.
- [x] 3.2 Run `ruff check .`, `ruff format --check .`, `ty check .`.
- [x] 3.3 Run the full test suite with coverage and confirm the 99%
      threshold holds.
- [x] 3.4 Start the application under xvfb and confirm the menubar is
      present with no warnings or tracebacks.
