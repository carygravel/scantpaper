# Tasks

## 1. Replace the outer pane with a box

- [x] 1.1 In `src/scantpaper/app.ui`, replace the vertical `GtkPaned` with a
  vertical `GtkBox` named `view_box`, keeping `vnotebook` as the expanding first
  child and `edit_hbox` as the non-expanding last child. Verify the builder
  loads the window and `pytest -q src/scantpaper/tests/test_app_ui.py` passes.
- [x] 1.2 In `src/scantpaper/app_window.py`, replace `_vpaned` and
  `_vpaned_initialised` with `_view_box`, and remove the manual
  `set_start_child`/`set_end_child` block for the notebook and `edit_hbox`.
  Verify a real-layout window builds and its image view is allocated a
  non-collapsed height.

## 2. Move the view container inside the box

- [x] 2.1 Update `_pack_viewer_tools` (and add a small swap helper if useful) so
  it removes the previous view container from `view_box` and inserts the
  notebook, horizontal pane or vertical pane above `edit_hbox`. Verify the
  existing packing, split-attach and orientation-switch tests pass with
  `GtkBox` child assertions.
- [x] 2.2 Remove the `end_at_minimum` parameter, the `keep_at_minimum` handler
  and the outer `_init_split_pane` call, leaving the initialiser to restore a
  saved position or use the half-split default for the inner panes. Verify the
  remaining `test_init_split_pane_*` tests and delete the two outer-pin tests.
- [x] 2.3 Replace every test reference to `_vpaned` with `_view_box` or a real
  window resize; in particular, replace `_vpaned.set_position(100)` in the
  hidden-canvas test with a window height change. Verify
  `pytest -q src/scantpaper/tests/test_app_window.py` passes.

## 3. Prove the fixed-row behaviour and document it

- [x] 3.1 Add real-layout tests that the edit bar is allocated inside the
  window immediately after selecting the Text layer page, that the view shrinks
  by the bar's height, that returning to the Image page reclaims that height,
  that switching from the Image page to a split view lays the bar out without a
  resize, and that a window resize leaves the bar at its natural height. Verify
  the tests fail before the layout change and pass after it.
- [x] 3.2 Update the layer-editing section of `README.md` to say the edit bar
  has a fixed height and cannot be resized by dragging, and add a `changelog.md`
  entry for the immediate show/hide fix and the removed divider. Verify
  `pytest -q src/scantpaper/tests/test_markdown_line_length.py` passes (ignoring
  the coverage gate for this partial run).

## 4. Integration checks

- [x] 4.1 Run `ruff format --check .`, `ruff check .`, `ty check .` and the full
  `pytest` suite, and confirm the coverage gate still passes with no new
  uncovered or partially covered lines.
- [x] 4.2 Run `openspec validate --specs --strict --no-interactive` and
  `openspec validate --archived --no-interactive`, plus
  `openspec validate make-edit-bar-a-fixed-row --strict --no-interactive`, and
  confirm they pass.
