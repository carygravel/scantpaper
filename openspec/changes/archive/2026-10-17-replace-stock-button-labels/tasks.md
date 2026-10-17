## 1. Replace stock-ID button labels

- [x] 1.1 In `tools_menu_mixins.py`, replace all `gtk-apply`/`gtk-cancel`/
      `gtk-ok` labels with `_("_Apply")`/`_("_Cancel")`/`_("_OK")`.
- [x] 1.2 In `dialog/scan.py`, replace `gtk-close` with `_("_Close")`.
- [x] 1.3 In `dialog/__init__.py` (`MultipleMessage`), replace `gtk-close`
      with `_("_Close")`.
- [x] 1.4 In `dialog/save.py`, replace `gtk-ok`/`gtk-cancel` with
      `_("_OK")`/`_("_Cancel")`.
- [x] 1.5 In `dialog/preferences.py`, replace `gtk-ok`/`gtk-cancel` with
      `_("_OK")`/`_("_Cancel")`.
- [x] 1.6 In `file_menu_mixins.py`, replace `gtk-save`/`gtk-cancel` with
      `_("_Save")`/`_("_Cancel")`.
- [x] 1.7 In `edit_menu_mixins.py`, replace `gtk-ok`/`gtk-cancel` with
      `_("_OK")`/`_("_Cancel")`.
- [x] 1.8 In `scan_menu_item_mixins.py`, replace `gtk-ok`/`gtk-cancel` with
      `_("_OK")`/`_("_Cancel")`.

## 2. Tests

- [x] 2.1 Update `test_tool_menu_mixins.py` to pick the apply/cancel
      callbacks by position instead of by stock-ID string.
- [x] 2.2 Update `test_dialog_save.py` and `test_052_dialog_save.py` the
      same way.
- [x] 2.3 Update `test_edit_menu_mixins.py` and
      `test_scan_menu_item_mixins.py` the same way.
- [x] 2.4 Add a test asserting the scan dialog's dismiss button carries the
      localised "Close" label and is not a stock ID.
- [x] 2.5 Add a guard test that fails if any production source contains a
      `"gtk-` stock-ID literal.

## 3. Documentation and gates

- [x] 3.1 Confirm README needs no change.
- [x] 3.2 Run `ruff check .`, `ruff format --check .`, `ty check .`.
- [x] 3.3 Run the full test suite with coverage and confirm the 99%
      threshold holds.
- [x] 3.4 Verify the scan dialog under xvfb shows a "Close" button with no
      warnings or tracebacks.
- [x] 3.5 Regenerate the translation template
      (`PYTHONPATH=src python3 dev/generate_pot.py`) so the new labels are
      picked up.
