# Tasks

## 1. Make `None` a safe selection value

- [x] 1.1 Update `_view_selection_changed_callback` to store `None` instead of
  calling `sel.copy()` unconditionally. Add a test that clears a populated
  selection and asserts `settings["selection"] is None` with no exception.
- [x] 1.2 Update `_on_view_selection_notify` to mirror `None` for property
  writes such as the Crop binding. Add a test that a `notify::selection` with
  `None` leaves the settings mirror empty rather than stale.
- [x] 1.3 Add a `None` branch to `Crop.selection` that clears `_selection`,
  zeroes the spin buttons under the existing `_updating_selection` guard, and
  emits `changed-selection`. Add a test that assigning `None` does not raise
  and leaves the dialog with no active selection.

## 2. Add the clear action and View menu item

- [x] 2.1 Register `clear-image-selection` in `_init_actions` and implement
  `clear_image_selection` with the order from `design.md`: settings first,
  then `view.set_selection(None)`, then the cached Crop selection. Add a test
  that activating the action clears both the view and the settings mirror.
- [x] 2.2 Add the View-menu item to `app.ui` after the Pan / Select /
  Select & pan group, labelled "Clear image selection". Add a UI-loading test
  that the menu model exposes `win.clear-image-selection`.
- [x] 2.3 Drive the action's sensitivity from `notify::selection` with
  `sel is not None`, initializing it disabled and guarding the lookup before
  the viewer exists. Add tests for disabled at startup, enabled after drawing,
  and disabled after clearing. Do not add it to the page-selection loop in
  `_update_uimanager`.
- [x] 2.4 Document the View-menu item in `README.md` and verify the text
  matches the shipped label and placement.
- [x] 2.5 Regenerate the translation template with
  `PYTHONPATH=src python3 dev/generate_pot.py` and verify the new label is
  present and `PYTHONPATH=src python3 dev/check_po.py` still passes.
- [x] 2.6 Add a toolbar button bound to `win.clear-image-selection` directly
  after the Pan / Select / Select & pan tools, using the `edit-clear` icon and
  the tooltip "Clear image selection". Add a UI-loading test for its action,
  icon, tooltip, and placement. Document the toolbar button in `README.md` and
  regenerate the translation template for the new tooltip.

## 3. Bind Escape

- [x] 3.1 Add `"win.clear-image-selection": ["Escape"]` to
  `Application._setup_accelerators` and add a test that asserts the
  registration.
- [x] 3.2 Verify that the text-layer editing control registers no Escape
  shortcut that would shadow the accelerator, so a focused control that
  handles Escape keeps the key. Inspect the control's shortcut controllers
  and confirm the accelerator remains the only Escape handler.
- [x] 3.3 Add the Escape shortcut to the keyboard table in `README.md` and
  verify the table row is present.

## 4. Integration checks

- [x] 4.1 Run the full test suite with coverage and verify the gate passes
  with no newly uncovered or partially covered lines other than type-only
  imports under `if TYPE_CHECKING:`.
- [x] 4.2 Run `ruff format --check`, `ruff check`, and `ty check .` and verify
  they report no issues.
- [x] 4.3 Run `openspec validate clear-image-selection --type change --strict
  --no-interactive`, `openspec validate --specs --strict --no-interactive`,
  and `openspec validate --archived --no-interactive`, and verify all pass.
- [x] 4.4 Smoke-test the user-visible behavior: draw a selection, clear it
  from the View menu, clear it with Escape, navigate pages, and confirm Add is
  disabled and Crop reports no region; verify the rectangle never appears in a
  saved PDF.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result with the archived-change validation command.
