# Tasks

## 1. Application Accelerator Table

- [x] 1.1 Remove `cut`, `copy`, `paste`, `select-all`, `undo`, `redo`,
  `zoom-in` and `zoom-out` from `_setup_accelerators()` in
  `src/scantpaper/app.py`. Verify with `pytest src/scantpaper/tests/test_app.py`
  that the moved actions report no application accelerators.
- [x] 1.2 Extend `src/scantpaper/tests/test_app.py` to assert the remaining
  accelerators, including Escape and the universal file and edit shortcuts,
  are unchanged. Verify the test fails if any moved accelerator is
  reintroduced.

## 2. Window Key Handling and Documentation

- [x] 2.1 Add helpers in `src/scantpaper/app_window.py` to detect whether the
  current focus widget is a text input (`Gtk.TextView` or `Gtk.Editable`) and
  to normalize key values and modifier state. Verify with unit tests covering
  a text view, an entry, and a non-text widget.
- [x] 2.2 Extend `_on_key_press()` to activate the corresponding window action
  for Ctrl+X, Ctrl+C, Ctrl+V, Ctrl+A, Ctrl+Z, and Ctrl+Shift+Z. Verify with
  tests for each key both outside a text control (action runs) and with a text
  control focused (no page action).
- [x] 2.3 Extend `_on_key_press()` to activate zoom in and zoom out for `+`,
  `-`, keypad `+`, and keypad `-` when focus is outside a text control. Verify
  with tests for the main and keypad keys, and with a text control focused.
- [x] 2.4 Restrict page deletion in `_on_key_press()` to an unmodified Delete
  press and leave Shift+Delete, Ctrl+Delete, and Alt+Delete alone. Verify with
  tests for plain Delete and each modified variant.
- [x] 2.5 Update the Keyboard Shortcuts section of `README.md` to state that
  text controls keep standard editing keys and printable `+` and `-`, while
  page and zoom shortcuts apply when focus is elsewhere and the mouse wheel
  zooms over the image. Verify the documented keys match the implementation and
  the Markdown lines stay within 80 characters.
- [x] 2.6 With text focus and with page-list focus, open the Edit and View
  menus and confirm every affected action is still present and enabled. Note
  whether shortcut hints are displayed; their presence is cosmetic and does
  not block the change.

## 3. Verification

- [x] 3.1 Run the full suite with `pytest` and confirm the coverage gate still
  passes with no new uncovered or partially covered lines.
- [x] 3.2 Run `ruff format --check`, `ruff check`, and `ty check .` and confirm
  all three are clean.
- [x] 3.3 Smoke-test the running application in tabbed and split views: focus
  the layer text control and type `+`, `-`, and the standard editing
  shortcuts, then verify no page or zoom action runs. Focus the page list and
  verify page cut/copy/paste/select-all/undo/redo and `+`/`-` zoom still work.

## Workflow follow-up

- Run `openspec validate --specs --strict --no-interactive`.
- Archive the change after maintainer review, then run
  `openspec validate --archived --no-interactive`.
