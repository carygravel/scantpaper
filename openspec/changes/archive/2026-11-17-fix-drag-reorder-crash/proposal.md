# Proposal

## Why

Dragging a page to a new position in the thumbnail list terminates scantpaper
with a hard segmentation fault, on every supported toolkit and display
combination tried (GTK 4.14.5 on Ubuntu 24.04 X11, and the reporter's
GTK 4.22.4 on Ubuntu 26.04 Wayland). The crash is silent to Python logging:
the app's custom GTK4 drag-and-drop arms the deprecated `GtkTreeView`
drop-highlight via `set_drag_dest_row()`, but never creates the internal
`TreeViewDragInfo` object that GTK's highlight repaint dereferences, so
`gtk_tree_view_bin_snapshot()` (gtktreeview.c:4849) reads through a NULL
pointer the first time the tree view paints the drag indicator. The result is
that the core page-reordering feature is unusable: the order of pages can no
longer be changed.

## What Changes

- The drag-and-drop reorder preview no longer uses GTK's native
  `set_drag_dest_row()` highlight, which crashes a `GtkTreeView` when its
  `TreeViewDragInfo` has never been created by the deprecated
  `gtk_tree_view_enable_model_drag_source/dest()` helpers.
- Starting a page drag, moving over the list, and dropping must never
  terminate the process and never trigger a GTK native fault, on the
  supported toolkit floor (GTK 4.6, jammy) through current releases
  (GTK 4.24), on both X11 and Wayland.
- The existing reorder semantics stay unchanged: the drag still dispatches a
  single worker-thread reorder operation, recorded as one undo step, without
  duplicating stored images, and keeps page numbers consecutive and the moved
  pages selected (all already specified under `page-reordering`).
- Where the drop position is still shown to the user, the feedback is provided
  by a mechanism that does not depend on GTK tree-view drag internals; if no
  floor-safe feedback mechanism is adopted, the preview is omitted rather than
  crashing (the choice is decided in the design).
- The fix is verified by a regression test that exercises the drag-to-reorder
  path, so a future re-introduction of the crashing pattern is caught in CI
  rather than on a user's machine.

## Capabilities

### New Capabilities

<!-- None: this change hardens an existing, already-specified behavior. -->

### Modified Capabilities

- `page-reordering`: add a requirement that the drag-and-drop interaction
  SHALL NOT crash the process or corrupt the UI when the drop feedback is
  rendered, and that reordering SHALL remain usable across the supported
  toolkit floor and current releases.

## Impact

- **Code:** `src/scantpaper/basedocument.py` (the custom `Gtk.DragSource` /
  `Gtk.DropTarget` controller wiring and `reorder_pages` dispatch) and
  `src/scantpaper/app_window.py` (`drag_motion_callback`, the sole caller of
  `set_drag_dest_row`). A custom drop-position indicator, if adopted, touches
  the thumbnail list rendering in `src/scantpaper/simplelist.py` or
  `basedocument.py`.
- **Tests:** `src/scantpaper/tests/test_basedocument.py` and
  `src/scantpaper/tests/test_app_window.py` cover the drop handlers; a
  regression test for the crash is added.
- **Dependencies:** none added or removed. The implementation must stay
  within the GTK 4.6 / PyGObject 3.42 floor (Ubuntu 22.04 jammy, supported
  until 2027-06) defined by `platform-compatibility`.
- **Upstream:** no upstream report will be filed. The NULL-deref lives in
  `gtk_tree_view_bin_snapshot`, a `GtkTreeView` code path; `GtkTreeView` has
  been deprecated since GTK 4.10, so upstream will not fix a crash in it.
  The fix is therefore entirely app-side, and eliminating the deprecated
  dependency belongs to a future `GtkListView`/`GtkColumnView` migration.
