## Context

The image-view re-fit change (fix-imageview-display) made the view's
zoom/offset dynamic: they now change on every allocation. The canvases
mirror zoom/offset through bidirectional GObject bindings and the layer
editor pushes the view's offset explicitly when a layer loads
(`LayerEditor.set_extent`, `create` → `canvas.set_offset`). Both paths
converge on `Canvas.offset`'s setter, which clamps against
`get_allocation()` (canvas.py:584) before storing. See proposal.md for
the verified failure: in tabbed mode the canvases are hidden
`GtkStack` pages — `0x0` before first show, frozen at a stale size
afterwards — so every push while hidden is clamped against a dead
allocation and nothing re-syncs when the canvas is shown.

Constraints:

- GTK 4.6.9 floor (jammy): `do_size_allocate` vfunc, GObject bindings —
  all available.
- The offset setter must keep ignoring pushes before the page extent is
  known (`get_pixbuf_size() is None`) — a clamp needs a page size, and
  an offset without one is meaningless. That guard is correct today and
  stays.
- `clear_text()` resets the extent; a stale stored offset must not
  survive into that state unnoticed (it is harmless — the setter
  ignores pushes with no extent — but re-clamping on allocation must
  also respect the no-extent guard).
- The canvases are also driven directly in split views (both visible at
  once); the fix must not change interactive behaviour there.

## Goals / Non-Goals

**Goals:**

- A pushed offset survives an unusable-allocation state and is clamped
  correctly at the next allocation.
- A canvas shown after being hidden displays the same page region as
  the image view.
- Interactive panning/zooming on either widget still propagates to the
  other (split-view behaviour unchanged).
- No clamping against a stale allocation ever leaves the page
  off-screen.

**Non-Goals:**

- Reworking the zoom/offset bindings into a single-source-of-truth
  ownership model (the explored Direction C) — deferred; the
  defer-and-recover fix removes the user-visible harm at far less
  risk.
- Persisting per-canvas offsets across page switches.
- Changing the canvas's zoom property behaviour (already safe — the
  zoom setter never clamps against the allocation).

## Decisions

**D1. Defer clamping while the allocation is unusable; re-clamp on
allocation.** In the offset setter, when `get_allocation()` reports a
zero width or height, store `newval` unclamped (after the existing
no-extent guard) and skip clamping and the change-notifications
(entirely — nothing is "changing" yet, the value is pending). Add a
`do_size_allocate` override that chains up, then re-clamps the stored
offset against the new allocation and emits `offset-changed` +
`queue_draw()` when it changes. This is the same defer-and-recover
shape the image view now uses for zoom-to-fit.
Alternatives considered: re-pushing the view's offset at show time via
a canvas→view reference (Direction B) — rejected as the primary
mechanism because it needs a new widget coupling; deriving the
transform from the view at draw time (Direction C) — rejected for
scope (touches layer.py interactions and every offset clamp site).

**D2. Stale-but-nonzero allocations are handled by D1's
allocation-time clamp, not by guessing staleness.** After a window
shrink, a hidden canvas holds an old allocation; a push clamped
against it would be wrong. With D1 the authoritative clamp always runs
at allocation time against the live allocation, so a wrongly-clamped
intermediate value cannot persist: every allocation re-clamps the
stored offset. No staleness tracking, no extra state.

**D3. The re-clamp on allocation emits normally.** When the
allocation-time clamp changes the offset, the setter's usual
notifications fire (`offset-changed` signal + GObject notify), so the
bidirectional bindings propagate the healed value to the view. GObject
bindings' transfer mask already prevents ping-pong. If the clamped
value equals the stored one, nothing is emitted — allocations are
frequent and the no-op path must stay silent.

**D4. Same guard for the view's offset setter.** The image view's
offset setter clamps the same way; while the view is a hidden stack
page (text tab active), a canvas-driven push clamps against its frozen
allocation. The view self-heals on re-allocation (zoom-to-fit), so a
defer guard there is defence in depth: apply the identical
unusable-allocation skip (store unclamped, clamp on allocate) so the
view also never clamps against `0x0`. Interactive behaviour when
visible is unchanged.

**D5. Minimum content sizes and a clamped position restore.** Found
during implementation: a split view's saved divider position can
collapse a pane after the migration's geometry changes. The user's
config had `split panel v` = 278 saved when the inner pane was ~491 px
tall; the outer pane's new half-split default leaves the inner pane
279 px, so the restored 278 px position fills it and the canvas (end
child) is left a 1 px sliver — an empty pane, only in split views.
TwoGtkPaned facts drive the fix: the paned's own minimum request is
just the handle (children's minimums are ignored, GTK4 has no
`shrink` flag), and a position beyond `size − handle − child2_min`
overflows child2 past the pane instead of clamping. Therefore:

- `ImageView` and `Canvas` get minimum content sizes
  (`set_content_width/height`), so every pane has a real floor and the
  DrawingArea widgets can never be allocated to invisibility. (The
  original design rejected minimums as the primary fix; the
  persisted-position interaction is why they are now required.)
- `_init_split_pane` clamps the restored position into
  `[handle + child1_min, size − handle − child2_min]`, measured at
  tick time (the paned's minimum request is the handle size), so a
  stale saved position from an older geometry heals itself instead of
  hiding a pane.

## Risks / Trade-offs

- [Storing an unclamped offset means transient out-of-range values exist
  while unallocated] → Mitigation: every draw path reads the offset
  only when allocated (a `0x0` widget draws nothing), and the
  allocation-time clamp bounds it before any rendering can use it.
- [Allocation-time clamping emits during layout] → Mitigation: same
  pattern as the image view's re-fit — setters compare before emitting,
  so the emission happens at most once per actual change; the
  regression tests pump the main loop and assert stable final state.
- [`do_size_allocate` must not recurse into bindings that set the offset
  again] → Mitigation: D3's equality check makes a re-entrant push a
  no-op unless the value differs; the binding mask covers the transfer
  path (already relied upon today).
- [Tests must exercise real allocation to be meaningful] → Mitigation:
  follow the pytest-xvfb real-layout pattern from
  test_imageview.py's allocation tests rather than mocking
  get_allocation.

## Migration Plan

Single-branch change via `/opsx-apply`. Task order:

1. Regression tests first (TDD): real-layout tests for
   push-while-unmapped → clamp-on-allocate, tab-switch alignment, and
   shrink-then-show visibility.
2. `Canvas.do_size_allocate` override + deferred clamp in the offset
   setter (D1–D3).
3. Matching guard in `ImageView.offset`'s setter (D4).
4. Full gate: `pytest`, `ruff`, `ty check .`; no worse uncovered/partial
   line counts.

Rollback: revert the commit; no data or config migration involved.

## Open Questions

- None.
