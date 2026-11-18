# Spike Verdict — drag-reorder crash fix

Date: 2026-11-17. Toolchain: Python 3.12.3, GTK 4.14.5 (Ubuntu 24.04 base),
X11. Probe: throwaway `/tmp/opencode/spike_dnd.py` (not merged).

## Verdict

**A2c fails its gate. Fall back to A1** (design D1). The fix removes the
`set_drag_dest_row()` arming of the native drop highlight in
`drag_motion_callback`.

## Evidence

Probe replicates the app's DnD wiring (own `Gtk.DragSource` +
`Gtk.DropTarget` controllers, `drag_motion_callback`-style
`set_drag_dest_row`) on a plain `GtkTreeView`, then triggers the exact crash
path without a real pointer drag: `set_drag_dest_row()` arms
`priv->drag_dest_row`, and the next repaint draws the drop highlight.

| Phase | Setup | Result |
|---|---|---|
| baseline | current wiring | SIGSEGV (exit 139) |
| A2c | + `enable_model_drag_source(...)` | SIGSEGV (exit 139) |
| A1 | motion handler never calls `set_drag_dest_row` | exit 0, `NO_CRASH` |

The gdb backtrace from the reporter's repro (and the local core under
debuginfod dbgsym) names the site: `gtk_tree_view_bin_snapshot` at
gtktreeview.c:4849, `di->cssnode` dereferenced with `get_info()`/`cssnode`
NULL.

## Why A2c fails

`gtk_tree_view_enable_model_drag_source` (gtktreeview.c:12916) only calls
`ensure_info()`, allocating the `TreeViewDragInfo` struct. The `cssnode`
that line 4849 dereferences is created only in
`gtk_tree_view_enable_model_drag_dest` (gtktreeview.c:12962) — installing
GTK's own `AsyncDropTarget` wired to the model-level reorder, which would
bypass the worker-thread reorder and its single-undo snapshot. That is the
A3 path the design explicitly rejected. Enabling the source alone therefore
turns the crash from a NULL `di` into a NULL `di->cssnode`: same segfault.
A2c cannot keep the native highlight without the competing destination
controller.

## Scope of the A1 validation

The probe verifies the crash site directly (the A1 motion handler never arms
the highlight). The reorder dispatch, undo snapshot and selection semantics
are untouched by A1 by construction (only the *feedback* call is removed)
and are confirmed by the existing unit tests in tasks 2.3 and 3.x.
