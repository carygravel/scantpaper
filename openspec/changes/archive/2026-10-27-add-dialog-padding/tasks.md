# Tasks

## 1. Shared dialog padding

- [x] 1.1 Add `DIALOG_CONTENT_MARGIN` and `DIALOG_ROW_SPACING` to
  `src/scantpaper/const.py`, and verify
  `PYTHONPATH=src python3 -c "from scantpaper.const import DIALOG_CONTENT_MARGIN, DIALOG_ROW_SPACING"`
  succeeds.
- [x] 1.2 Set the content area's margins (via `helpers.set_margins`) and
  spacing in `Dialog.__init__` in `src/scantpaper/dialog/__init__.py` from the
  new constants, and verify a new test in
  `src/scantpaper/tests/test_05_dialog.py` asserts the content area carries the
  shared margin on all four sides and the shared spacing, with
  `pytest src/scantpaper/tests/test_05_dialog.py` passing.
- [x] 1.3 Document the dialog padding in `README.md` and verify a shown Tools
  dialog matches the description (inset from the edge, rows spaced).

## 2. Row spacing at the row sites

- [x] 2.1 Construct the row boxes in `src/scantpaper/tools_menu_mixins.py`
  (threshold, brightness/contrast, unsharp, split and user-defined) with
  `spacing=DIALOG_ROW_SPACING`, and verify
  `pytest src/scantpaper/tests/test_tool_menu_mixins.py` passes with a row box
  built at the shared spacing.
- [x] 2.2 Construct the row boxes in `src/scantpaper/dialog/crop.py` with
  `spacing=DIALOG_ROW_SPACING`, and verify
  `pytest src/scantpaper/tests/test_06_crop_dialog.py` passes with a crop row
  built at the shared spacing.
- [x] 2.3 Construct the row boxes in `src/scantpaper/unpaper.py` and
  `src/scantpaper/postprocess_controls.py` with `spacing=DIALOG_ROW_SPACING`,
  and verify `pytest src/scantpaper/tests/test_34_unpaper.py
  src/scantpaper/tests/test_postprocess_controls.py` passes with the option
  rows built at the shared spacing.
- [x] 2.4 Construct the row boxes in `src/scantpaper/dialog/scan.py`,
  `src/scantpaper/dialog/save.py`, `src/scantpaper/dialog/preferences.py`,
  `src/scantpaper/dialog/pagecontrols.py`, `src/scantpaper/dialog/sane.py`,
  `src/scantpaper/scan_menu_item_mixins.py`, `src/scantpaper/pagerange.py`,
  `src/scantpaper/file_menu_mixins.py` and `src/scantpaper/edit_menu_mixins.py`
  with `spacing=DIALOG_ROW_SPACING`, so Requirement 3 holds for every dialog,
  and verify their tests pass
  (`pytest src/scantpaper/tests/test_dialog_scan.py
  src/scantpaper/tests/test_dialog_save.py
  src/scantpaper/tests/test_preferences_dialog.py
  src/scantpaper/tests/test_pagecontrols.py
  src/scantpaper/tests/test_scan_menu_item_mixins.py
  src/scantpaper/tests/test_file_menu_mixins.py
  src/scantpaper/tests/test_edit_menu_mixins.py
  src/scantpaper/tests/test_05_dialog.py`).
- [x] 2.5 Route the five dialogs built on a bare `Gtk.Dialog` — in
  `src/scantpaper/session_mixins.py` (pick crashed session),
  `src/scantpaper/file_menu_mixins.py` (pages to extract) and
  `src/scantpaper/dialog/scan.py` (name/overwrite/edit profile) — through a
  shared `pad_content_area()` helper defined in
  `src/scantpaper/dialog/__init__.py` and also used by `Dialog.__init__`, so
  their content areas are inset too, and verify
  `pytest src/scantpaper/tests/test_05_dialog.py
  src/scantpaper/tests/test_session_mixins.py
  src/scantpaper/tests/test_file_menu_mixins.py
  src/scantpaper/tests/test_0621_dialog_scan_edit_save.py` passes with the
  padding applied.

## 3. Integration verification

- [x] 3.1 Run the full `pytest` suite and confirm every test passes and the
  coverage thresholds in `pyproject.toml` are met.
- [x] 3.2 Run `ruff format --check`, `ruff check` and `ty check .` and confirm
  all three are clean.

## Workflow follow-up

- Archive the change once the project's review requirements are satisfied.
- Verify the archived result: `dialog-layout` appears under
  `openspec/specs/`.
