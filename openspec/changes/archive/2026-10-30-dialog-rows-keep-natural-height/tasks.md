# Tasks

## 1. Scan dialog page options

- [x] 1.1 Remove the vertical expand requests from the `# Pages` rows ("All"
  check button, `#:` row) and the `Source document` rows ("Single sided",
  "Side to scan") in `dialog/pagecontrols.py`; verify a new case in
  `test_pagecontrols.py` asserts neither frame computes as vertically
  expanding and none of the four rows requests `vexpand`.
- [x] 1.2 Top-align the `Page Options` page box
  (`PageControls._notebook_pages[0]`) and verify the same test asserts its
  `valign` is `Gtk.Align.START`.
- [x] 1.3 Add a real-layout test that presents `Scan` at 450x1000, pumps the
  main loop, and asserts the `# Pages` frame and the "All" button are within a
  few pixels of their natural heights; verify the test fails before 1.1 and
  passes after it.
- [x] 1.4 Add a short-window layout test that presents `Scan` at 450x300 and
  asserts the page's vertical adjustment has more content than page size and
  the last row is reachable, so the top-align guard does not break scrolling.

## 2. Scan dialog Postprocessing page

- [x] 2.1 Remove `_side1.set_vexpand(True)` in `RotateControls` and verify a
  new case in `test_postprocess_controls.py` asserts `RotateControls` does not
  compute as vertically expanding and `_side1` does not request `vexpand`.
- [x] 2.2 Top-align the Postprocessing page box in
  `scan_menu_item_mixins.add_postprocessing_options` and verify a new case in
  `test_scan_menu_item_mixins.py`, using a real `Gtk.Notebook`, asserts the
  page's content box `valign` is `Gtk.Align.START`.
- [x] 2.3 Add a real-layout test that presents a scrolled page holding a real
  `RotateControls` at 450x1000 and asserts the rotate row is at its natural
  height.

## 3. Clean up dialog

- [x] 3.1 Remove the five vertical expand requests in the `unpaper.py` row
  helpers (`_add_combobox`, `_add_checkbutton`, `_add_checkbuttongroup`,
  `_add_spinbutton`, `_add_spinbuttongroup`); verify a new case in
  `test_34_unpaper.py` walks the first notebook page and asserts no row
  computes as vertically expanding.
- [x] 3.2 Add a real-layout test that presents the Clean up dialog at
  500x1000 and asserts the "Deskew" page rows are within a few pixels of their
  natural heights.

## 4. Preferences dialog

- [x] 4.1 Give the `General options` page box the same
  `valign=Gtk.Align.START` as the `Scan options` page and remove the row
  expand requests in `_add_general_options1`, `_add_general_options2`,
  `_add_bilevel_compression` and `_add_user_defined_tool_entry`; verify a new
  case in `test_preferences_dialog.py` asserts no row computes as vertically
  expanding and the page is top-aligned.
- [x] 4.2 Add a real-layout test that presents the Preferences dialog at
  500x1000 on the `General options` page and asserts the rows are within a few
  pixels of their natural heights.
- [x] 4.3 Update `README.md` and `changelog.md` to state that dialog rows keep
  their natural height and surplus height appears below the last row; verify
  the wording names the scan, Clean up and Preferences dialogs accurately.

## 5. Integration checks

- [x] 5.1 Run `pytest` and verify the full suite passes with no drop in
  line or branch coverage.
- [x] 5.2 Run `ruff format --check .`, `ruff check .` and `ty check .` and
  verify each reports no diagnostics.
- [x] 5.3 Run `openspec validate dialog-rows-keep-natural-height --strict`
  and verify it passes.

## Workflow follow-up

- Archive the change with `/opsx-archive-change` after review, which syncs the
  `dialog-layout` delta into the main spec.
- Verify the archived spec contains both added requirements and the existing
  page-range requirement.
