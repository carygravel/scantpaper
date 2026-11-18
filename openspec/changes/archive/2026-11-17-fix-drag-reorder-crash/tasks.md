# Tasks

## 1. Spike: validate A2c before implementing

- [x] 1.1 Confirm the pre-fix crash baseline against current HEAD: reproduce
      the drag-to-reorder segfault under gdb (capture a backtrace ending in
      `gtk_tree_view_bin_snapshot` at gtktreeview.c:4849), and record it as
      the known-bad reference for the fix (verification: recorded backtrace
      names `gtk_tree_view_bin_snapshot`).
- [x] 1.2 Build the A2c probe (throwaway, not merged): add a single
      `gtk_tree_view_enable_model_drag_source(...)` setup call to the
      thumbnail list and drive drag start/motion/drop; verify (a) no
      segfault, (b) the drop still dispatches `reorder_pages` to the worker
      and records exactly one undo snapshot, (c) the app's own
      `Gtk.DragSource`/`Gtk.DropTarget` controllers still fire and GTK does
      not install a competing drop target (verification: an observed
      crash-free drag in which undo restores the order in one step).
- [x] 1.3 Record the spike verdict in the change folder or PR description:
      "A2c passes" or "fall back to A1" (verification: the note exists and
      names the branch the implementation takes).

## 2. Implement the fix (branch chosen in 1.3: A1)

A2c was rejected by the spike (see spike-verdict.md): the dropped
`enable_model_drag_source` idea cannot create the cssnode the native
highlight needs without also installing GTK's own competing drop target
(the A3 path the design ruled out), so no A2c implementation task is
tracked.

- [x] 2.1 A1: remove `set_drag_dest_row()` and the dead
      `get_dest_row_at_pos()` path from `drag_motion_callback`, keep the
      auto-scroll, and leave `_on_drop_rows` destination logic unchanged
      (verification: existing `test_drag_motion_callback*` tests pass and no
      `set_drag_dest_row` call remains under `src/`).
- [x] 2.2 Confirm the deletion-guard machinery (`_suppress_delete` /
      `_on_drag_end`) is untouched and the reorder still lands the moved
      pages selected (verification: `test_reorder_data_moves_pages`,
      `test_reorder_pages_data_callback`, `test_reorder_then_stray_deletion_*`
      and `test_on_drop_rows_*` pass unchanged).

## 3. Regression coverage

- [x] 3.1 Add the unit regression test for the adopted branch: for A1,
      assert `drag_motion_callback` never calls `set_drag_dest_row`; for
      A2c, assert the tree view's drag info is created and the highlight
      path is exercised; verify the new test fails against the pre-change
      code (verification: test added that would have caught the crash).
- [x] 3.2 Assess a display-backed GTK integration test for CI: if a display
      or offscreen renderer is available, add an environment-gated test
      running drag start/motion/drop that asserts no process death;
      otherwise write the manual QA repro as a copy-paste runnable step list
      (verification: gated integration test present, or documented repro
      steps present and complete).
- [x] 3.3 Run the manual QA repro on X11 and, if available, Wayland:
      scan/import 2-3 pages, drag a page to a new position, undo
      (verification: reorder completes crash-free and undo restores the
      previous order in one step).

## 4. Changelog and docs

- [x] 4.1 Add a changelog entry for the crash fix and, if A1 is adopted,
      note the removed drop-line feedback in README.md (verification:
      entries exist and describe the fixed behaviour accurately).

## 5. Integration and quality gates

- [x] 5.1 Run `ruff format`, `ruff check` and `ty check .` on the touched
      modules and verify they are clean with no new suppressions.
- [x] 5.2 Run the full `pytest` suite with coverage and verify no newly
      uncovered or partially covered lines beyond the pre-existing baseline.

## Workflow follow-up

- Archive the change after project review is satisfied.
- Verify the archived result with `openspec validate --archived --no-interactive`.
- Revisit a custom drop-position indicator (design D3, A2b/A2a) as a
  separate change only if field feedback shows the removed highlight matters.
- No upstream GTK report: `GtkTreeView` is deprecated (4.10), so a crash
  report against it would not be fixed upstream; the fix is app-side, and
  the deprecation debt is tracked via the future
  `GtkListView`/`GtkColumnView` migration.
