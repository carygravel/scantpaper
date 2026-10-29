# Tasks

## 1. Shared action-area helper

- [x] 1.1 Add `DIALOG_BUTTON_SPACING = 6` to `src/scantpaper/const.py` with a
  comment explaining the GTK3-to-GTK4 change, and verify
  `PYTHONPATH=src python3 -c "from scantpaper.const import
  DIALOG_BUTTON_SPACING"` succeeds.
- [x] 1.2 Add `pad_action_area(dialog)` to
  `src/scantpaper/dialog/__init__.py`: reach the action area through the fixed
  content-area -> next-sibling -> first-child path, return without changes for
  an empty or homogeneous action area, and otherwise set the shared spacing
  and all four `DIALOG_CONTENT_MARGIN` margins. Add tests in
  `src/scantpaper/tests/test_05_dialog.py` for a normal `Dialog`, a bare
  `Gtk.Dialog`, an empty action area, a joined message dialog and a
  `Gtk.FileChooserDialog`, and verify
  `pytest src/scantpaper/tests/test_05_dialog.py` passes.
- [x] 1.3 Call `pad_action_area(self)` from `Dialog.add_actions()` after the
  buttons are added, and verify a `Dialog` with Apply and Cancel actions has
  the shared spacing and margins by running
  `pytest src/scantpaper/tests/test_05_dialog.py
  src/scantpaper/tests/test_dialog_buttons.py`.
- [x] 1.4 Update the **Dialogs** bullet in `README.md` and add an entry under
  4.0.2 in `changelog.md`. The wording must cover the action-button inset and
  spacing and must say that joined message-dialog bars are unchanged; verify
  by reading both files.

## 2. Bare `Gtk.Dialog` sites

- [x] 2.1 Import `pad_action_area` in `src/scantpaper/session_mixins.py` and
  call it after the crashed-session dialog's `add_button`; verify
  `pytest src/scantpaper/tests/test_session_mixins.py` passes.
- [x] 2.2 Import `pad_action_area` in `src/scantpaper/file_menu_mixins.py` and
  call it after the pages-to-extract dialog's `add_buttons`; verify
  `pytest src/scantpaper/tests/test_file_menu_mixins.py` passes.
- [x] 2.3 Import `pad_action_area` in `src/scantpaper/dialog/scan.py` and call
  it after each of the three profile dialog `add_buttons` calls; verify
  `pytest src/scantpaper/tests/test_0621_dialog_scan_edit_save.py
  src/scantpaper/tests/test_dialog_scan.py` passes.

## 3. File-chooser sites

- [x] 3.1 Call `pad_action_area` after the four `Gtk.FileChooserDialog`
  `add_buttons` calls in `src/scantpaper/file_menu_mixins.py`; verify
  `pytest src/scantpaper/tests/test_file_menu_mixins.py` passes.
- [x] 3.2 Import `pad_action_area` in `src/scantpaper/dialog/preferences.py`
  and call it after the temporary-directory chooser's `add_buttons`; verify
  `pytest src/scantpaper/tests/test_preferences_dialog.py` passes.
- [x] 3.3 Import `pad_action_area` in `src/scantpaper/postprocess_controls.py`
  and call it after the tessdata-directory chooser's `add_buttons`; verify
  `pytest src/scantpaper/tests/test_postprocess_controls.py` passes.

## 4. Integration verification

- [x] 4.1 Run the full `pytest` suite and confirm all tests pass and the
  coverage thresholds in `pyproject.toml` are met.
- [x] 4.2 Run `ruff format --check`, `ruff check` and `ty check .` and confirm
  all three are clean.
- [x] 4.3 Run
  `openspec validate "restore-dialog-action-button-spacing" --type change`
  and confirm the change is valid.

## Workflow follow-up

- Archive the change once the project's review requirements are satisfied.
- Verify the archived `dialog-layout` spec contains the action-area inset,
  button-spacing and joined-message-bar requirements.
