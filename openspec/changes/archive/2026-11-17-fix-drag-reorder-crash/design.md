# Design

## Context

The crash is a native NULL-deref in GTK's deprecated `GtkTreeView`
drop-highlight repaint (`gtk_tree_view_bin_snapshot`, gtktreeview.c:4849):
scantpaper's custom GTK4 drag-and-drop (own `Gtk.DragSource` +
`Gtk.DropTarget` controllers in `basedocument.py`) arms the highlight through
`set_drag_dest_row()` from `drag_motion_callback` (`app_window.py`), but the
`TreeViewDragInfo` object that GTK's highlight drawing dereferences is only
created by the deprecated `gtk_tree_view_enable_model_drag_source/dest()`
helpers, which the app never calls. `get_info()` therefore returns NULL and
the first highlight repaint dereferences NULL->0x20. See proposal.md - Why.

Constraints that shape the approach:

- **Toolkit floor:** GTK 4.6 / PyGObject 3.42 (Ubuntu 22.04 jammy, supported
  until 2027-06), per `platform-compatibility`. Any API newer than the floor
  needs runtime detection plus a fallback. The crash reproduces across GTK
  4.14 (local) and 4.22 (reporter), X11 and Wayland, and the fix must not
  regress any of them.
- **Architecture that must survive intact:** page reorders dispatch to the
  worker thread (`do_reorder_pages`), persist through the SQLite
  `page_order` undo snapshots, and are a single undo step. The
  `_suppress_delete()` / `_on_drag_end()` deletion-guard machinery is
  separate from the crash and must not be disturbed.
- **The highlight is feedback only.** `_on_drop_rows()` computes the drop
  index itself at drop time via `get_dest_row_at_pos()`; removing the motion
  handler's `set_drag_dest_row()` call cannot change where a drop lands.

## Goals / Non-Goals

**Goals:**

- Deterministically eliminate the native fault for the whole drag lifetime
  (start, motion, drop) on every supported GTK/display combination, while
  staying within the 4.6 API floor.
- Prefer preserving the current drop-highlight UX, but only on strong
  evidence that the mechanism is safe across the floor.
- Add a regression test that locks the fix in place in CI.
- Leave the worker reorder, undo snapshots, and deletion-guard machinery
  untouched.

**Non-Goals:**

- No migration to `GtkListView`/`GtkColumnView`. `GtkTreeView` is
  deprecated, not removed; migration is deprecation debt to be specced and
  costed separately (the jammy floor until 2027-06 is a hard constraint
  either way).
- No painted insertion-line feature (the A2a variant) in this change. It is
  a new rendering mechanism with no in-repo precedent (`Gtk.Overlay` is not
  used anywhere today); it is deferred to a separate proposal.
- No upstream report and no dependency on an upstream GTK fix. The missing
  NULL guard in `gtk_tree_view_bin_snapshot` cannot be fixed upstream
  (`GtkTreeView` is deprecated since 4.10), so the app-side fix is the
  complete mitigation for this crash, and migration off `GtkTreeView` is
  the tracked debt that eventually removes the deprecated dependency.

## Decisions

### D1: Fix the highlight by spike-gating A2c, with A1 as the fallback

- **A2c (preferred if it verifies):** call
  `gtk_tree_view_enable_model_drag_source(...)` once at thumbnail-list setup.
  Per the GTK 4.14 source read during investigation, this helper calls
  `ensure_info()` (creating exactly the `TreeViewDragInfo` the highlight
  needs) and only configures the info's source fields - it does not install
  a competing drop target on the destination side. If that holds across the
  floor, the current highlight UX survives for near-A1 effort.
  - *Why not A3 (also call `enable_model_drag_dest`)?* The destination-side
    helper installs GTK's own `AsyncDropTarget` wired to the model-level
    reorder, which would bypass the worker-thread reorder and the undo
    snapshots - breaking the single-undo contract. A2c deliberately touches
    only the source side.
  - *Gate:* a spike verifies, on GTK 4.6 and a current GTK: (1) no crash
    across drag start/motion/drop; (2) the drop still dispatches
    `reorder_pages` to the worker (no GTK model-level reorder, still one
    undo step); (3) the app's own `Gtk.DragSource` controller still works
    alongside GTK's source-side setup. If any check fails, fall back to A1.
- **A1 (fallback, guaranteed):** stop calling `set_drag_dest_row()` (and
  drop the now-dead `get_dest_row_at_pos()`/path computation) in
  `drag_motion_callback`, keeping the auto-scroll. This removes the code
  that arms the crashing highlight; existing tests already pass because they
  assert scroll/action behaviour, not the highlight. This is the safe
  floor of the change and ships regardless if A2c fails its gate.

Rationale: A2c keeps the UX users have today for nearly the cost of A1, but
it rests on the same deprecated internals that broke - so it earns its place
only through the empirical gate. A1 deletes the risky call outright. Both
stay within the 4.6 floor (`enable_model_drag_source` exists since GTK 3).

### D2: Regression test locks the behavioural contract

- Assert at unit level that `drag_motion_callback` no longer arms the
  native highlight (no `set_drag_dest_row` call) unless A2c is adopted, in
  which case assert the drop-highlight path is exercised without reaching
  the NULL `TreeViewDragInfo` state.
- Because the original crash is native and needs a realised tree view, a
  full integration test may not run headlessly in CI; the unit-level
  assertion plus a manual QA step (enumerated in tasks) covers the gap. The
  feasibility of a display-backed GTK integration test is left to
  implementation time and does not change this design.
- Keep the existing `test_drag_motion_callback*` scenarios (scroll and
  action return values) intact.

### D3: Defer the richer drop-position indicator

A2b (textual "insert before/after page N") and A2a (painted insertion line)
are deliberately not part of this change. The A2c-or-A1 choice already gives
either the full current feedback or none; the cost of a custom indicator is
better justified once field use shows whether the missing highlight is
actually felt.

## Risks / Trade-offs

- [A2c rests on deprecated `GtkTreeView` internals] → gated by the spike;
  A1 is the pre-approved fallback, so the change never ships unsafe.
- [A2c could let GTK's own source setup interfere with the app's
  `Gtk.DragSource` controller] → spike check (3); A1 removes both concerns
  if needed.
- [A1 is a quiet UX regression: the precise before/after boundary line
  disappears during a drag] → self-confirming operation (list visibly
  reorders, moved pages stay selected), off-by-one is one undo away;
  A2b/A2a is tracked as a follow-up.
- [A native GTK crash may not be capturable by a headless CI test] →
  unit-level behavioural assertion always runs; display-backed check is
  manual QA (documented in tasks).
- [API drift across 4.6 → 4.24 could change helper behaviour after A2c
  ships] → the platform-compat spec's render-tree inspection can be reused
  to catch regressions; A2c's footprint is a single setup call, cheap to
  revisit.

## Migration Plan

- Pure bug fix: no data or state migration. Ships in the next release.
- Rollback is trivial: revert to the pre-change drag path; the crash is no
  worse than the status quo of this report.
- No upstream GTK report will be filed: `GtkTreeView` has been deprecated
  since GTK 4.10 and a report against its internal crash would not be
  fixed. Removing the deprecated dependency is tracked as the future
  `GtkListView`/`GtkColumnView` migration.

## Open Questions

- Whether CI can host a display-backed GTK crash regression - implementation
  time determines this; it does not alter the spec, the approach, or the
  task list, because the unit-level assertion already encodes the
  behavioural contract.
