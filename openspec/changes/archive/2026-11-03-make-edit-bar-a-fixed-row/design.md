# Design

## Context

See `proposal.md` - Why for the failure the user sees. The current layout in
`src/scantpaper/app.ui` nests a vertical `GtkPaned` (`vpaned`) inside the
horizontal thumbnail pane. Its start child is the notebook, or an inner split
pane, and its end child is `edit_hbox`, the always-visible container for the
layer control bars.

`ApplicationWindow._pack_viewer_tools` swaps the outer pane's start child
between the notebook and the horizontal or vertical inner split pane. At
startup `_init_split_pane(..., end_at_minimum=True)` pins the outer divider to
the bar's minimum height, and `keep_at_minimum` re-pins it on
`notify::max-position`. `edit_hbox` itself never changes visibility: the
`LayerControls` inside it do, which leaves the divider where it was. The outer
divider is not persisted; only the inner split positions (`split panel h` and
`split panel v`) are.

The inner panes must keep their current behaviour: a half-split default, a
saved-position restore, and the equal-resize sharing already in
`_SplitResizeSharer`.

## Goals / Non-Goals

**Goals:**

- Give the edit bar a fixed, natural height and lay it out as soon as its
  controls appear or disappear, without a window resize.
- Give every pixel that the bar does not use to the view above it.
- Keep the inner horizontal/vertical split behaviour and position persistence
  unchanged.
- Delete the outer-pane pinning machinery instead of extending it.

**Non-Goals:**

- Changing the contents, ordering or visibility rules of the layer controls.
- Providing another way to enlarge the edit bar.
- Moving the scanner progress bar or changing its lifecycle.
- Changing saved window size or inner split position settings.

## Decisions

### Replace the outer pane with a vertical box

Use a vertical `GtkBox` (`view_box`) whose first child is the view container
and whose last child is `edit_hbox`. The view container expands; `edit_hbox`
does not, so it receives exactly its natural height and the view receives the
rest.

A `GtkBox` re-negotiates when a descendant's size request changes, so showing
or hiding `LayerControls` changes the bar's height immediately. This removes
the need to listen for `notify::max-position` and removes the stale-divider
state entirely.

Alternatives considered:

- Re-pin the divider on each control visibility change (option A from the
  exploration). Smaller diff, but keeps a divider that is neither persisted nor
  honoured on the next resize, and leaves two sources of truth for the bar's
  height. Rejected in favour of the chosen fixed row.
- Reserve the bar's height permanently and hide only its contents. Wastes space
  on the Image page. Rejected.

### Keep `_pack_viewer_tools` as the single view-container swap point

The method already centralises the notebook/inner-pane transition. Change it to
remove the current view container from `view_box` and prepend the new one, so
the order stays view then bar. `_dock_view_and_layer` keeps building the inner
panes.

The explicit `set_start_child`/`set_end_child` block in `ApplicationWindow`'s
initialiser goes away: the `.ui` already places the notebook above the bar.

Alternatives considered:

- Keep the `vpaned` identifier and only change its class. Less test churn, but
  leaves `_vpaned` and `vpaned` naming a box and invites future mistakes.
  Rejected in favour of `view_box`/`_view_box`.

### Remove `end_at_minimum` from the split-pane initialiser

With no outer pane, `_init_split_pane` only positions the inner horizontal and
vertical panes. Drop the `end_at_minimum` parameter, the `keep_at_minimum`
handler and the `_vpaned_initialised` flag. The initialiser keeps restoring a
saved position or choosing the half-split default.

### Let the box handle progress-bar and window-size changes

The scanner progress bar lives outside this box, in the window's top-level
column. When it disappears the box and view simply get more height; the edit
bar keeps its natural height. No pin or tick callback is needed.

### Update layout tests to assert allocations, not divider positions

Replace the outer-pane pin tests with real-layout assertions:

- after selecting a layer page, `edit_hbox` is allocated inside the window and
  the view has shrunk by the bar's height;
- after returning to the Image page, the view has reclaimed that height;
- switching from the tabbed Image page to a split view lays the bar out without
  a resize;
- resizing the window keeps the bar at its natural height.

The mocked packing tests change from `Gtk.Paned` start-child assertions to
`GtkBox` child-order assertions. The test that shrinks the view while the
canvas is hidden uses a window resize instead of `_vpaned.set_position(100)`.

## Risks / Trade-offs

- **The user loses the ability to enlarge the text field by dragging the bar**
  → Accepted; the divider was not persisted and snapped back on the next pane
  resize, so it was not a dependable feature. The proposal marks it as a UI
  breaking change and the README will say the bar has a fixed height.
- **A mocked `_view_box` may not model `GtkBox` child management** → Keep the
  swap in one helper and test that helper with a real `GtkBox` in the
  split-attach test, as the existing paned test did.
- **Reordering the box children could put the bar above the view** → The helper
  removes every child except `edit_hbox` and prepends the view container, so
  the bar is always last.
- **Real-layout tests become flaky if they assert exact pixel heights** →
  Assert relative changes (inside the window, view height decreases by the
  bar height, no change after a resize) rather than hard-coded geometry.

## Migration Plan

No data migration is needed: the outer divider position was never persisted.
Window size, thumbnail divider and inner split positions keep their existing
settings and restore paths. Rollback is a code and `.ui` revert; no session or
configuration state is rewritten.
