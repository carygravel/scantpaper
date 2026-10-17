## Why

Dialog action buttons display raw GTK3 stock IDs: the scan dialog's close
button reads "gtk-close", and other dialogs show "gtk-ok", "gtk-cancel",
"gtk-apply" or "gtk-save". GTK4 removed stock IDs, so those strings are used
verbatim as button labels, are untranslatable, and lost the mnemonics the
stock buttons used to provide.

## What Changes

- Replace every GTK stock-ID literal passed as a dialog button label with a
  translated label: `gtk-ok` → `_("_OK")`, `gtk-cancel` → `_("_Cancel")`,
  `gtk-close` → `_("_Close")`, `gtk-apply` → `_("_Apply")`,
  `gtk-save` → `_("_Save")`.
- Update the tests that select a button's callback by its stock-ID string to
  select it by position instead, so they no longer key on the ID.
- Add a guard test that fails if a stock-ID literal reappears in production
  source.

## Capabilities

### New Capabilities

- `dialog-buttons`: dialog action buttons present localised, mnemonic-bearing
  labels and never display GTK stock IDs.

### Modified Capabilities

None.

## Impact

- `tools_menu_mixins.py` (threshold, brightness/contrast, negate, unsharp,
  crop, unpaper, OCR, user-defined, email dialogs), `dialog/scan.py`,
  `dialog/save.py`, `dialog/preferences.py`, `dialog/__init__.py`
  (`MultipleMessage`), `edit_menu_mixins.py`, `file_menu_mixins.py`,
  `scan_menu_item_mixins.py`.
- Tests: `test_052_dialog_save.py`, `test_dialog_save.py`,
  `test_edit_menu_mixins.py`, `test_scan_menu_item_mixins.py`,
  `test_tool_menu_mixins.py`; one new guard test.
- Label strings become translatable, so translation templates gain five
  short messages.
- No new dependencies; behaviour is otherwise unchanged.
