## Context

The GTK4 migration (e4e067a2) left the image view unable to display pages
after scan/import. See proposal.md for the verified root causes: a layout
collapse of the outer `_vpaned` (all viewer modes) and a dead
`notify::width`/`notify::height` re-fit hook in `ImageView`.

Constraints that shape the fix:

- The app must keep running on GTK 4.6.9 (Ubuntu 22.04 jammy floor). The
  fix may only use APIs available by 4.6: `do_size_allocate` vfunc,
  `Gtk.Paned.set_position`, `Gtk.DrawingArea.set_content_*` — all fine.
- CI runs pytest under pytest-xvfb (`.github/workflows/test.yml`), so real
  widget layout can be exercised in tests.
- `_init_split_pane` (app_window.py:535) already implements "give a paned
  a usable default position on first allocation" via a tick callback, and
  is applied to the inner panes (`_hpanei`/`_vpanei`) in split modes only.
- `_pack_viewer_tools` runs twice in a session's life: at startup
  (session_mixins.py:458) and on every view-mode switch
  (app_window.py:752).

## Goals / Non-Goals

**Goals:**

- The page is visible in the image view after scan/import in every viewer
  mode, without any user interaction.
- Zoom-to-fit recomputes on every allocation change (first allocation,
  window resize, divider drag, view-mode switch) while `zoom_is_fit` is
  active.
- The draw path never dereferences a `None` offset.
- Regression tests that fail on the current code and pass after the fix.

**Non-Goals:**

- Persisting the outer `_vpaned` divider position (new config setting) —
  GTK3 never persisted it either; a follow-up change can add it.
- Fixing the inner-pane tick callbacks that spin forever when their parent
  is collapsed (they become unreachable once the outer pane is sized; a
  guard can ride along only if trivial).
- Modernising deprecated APIs (`get_style_context`, `Gtk.Dialog`) beyond
  what the fix touches.
- Re-positioning the divider on view-mode switches (see D3).

## Decisions

**D1. Replace the dead notify handlers with a `do_size_allocate` vfunc
override.** GTK4's canonical replacement for the GTK3 configure-event is
the `size_allocate` vfunc: it fires on every allocation with the widget's
allocation already updated. The override chains up to the parent class
first, then re-runs `zoom_to_box()` when `zoom_is_fit` is active.
Alternatives considered: connecting to the parent paned's `size-allocate`
signal (deprecated since 4.12); detecting size changes inside the draw
func (re-enters layout from a draw — fragile); a tick callback (polling
overhead, another source to manage). The migration's
`notify::width`/`notify::height` approach was correct in spirit — the
properties simply do not exist on `GtkWidget`, and the tests mocked the
allocation so nothing caught it. Ordering note: the override must chain
up before reading the allocation; a test asserts the re-fit sees the new
allocation.

**D2. Initialise the outer `_vpaned` divider in every viewer mode by
reusing `_init_split_pane`.** In tabbed mode, call it on `_vpaned`
(no saved position — always apply the default); in split modes, call it
on `_vpaned` in addition to the existing inner-pane calls, so the inner
panes receive real space instead of being starved to 0x0 (which today
also strands `_init_split_pane`'s tick callback in a `size <= 1` loop).
The default share is half the pane, consistent with the inner panes'
existing behaviour. Alternatives considered: giving `ImageView`/`Canvas`
real minimum sizes via `set_content_width/height` — rejected as the
primary fix because a minimum only lifts the collapse floor, it does not
produce a sensible default share; and restoring GTK3's exact distribution
(child1 gets everything but child2's minimum) — rejected as a new
divergent code path when half is already the established default in this
codebase. Zoom-to-fit makes any share usable.

**D3. Apply the default position only on first packing, not on every view
switch.** `_pack_viewer_tools` runs again on `_change_view_cb`; resetting
the divider then would discard the user's adjustment mid-session. The
outer `_vpaned` initialisation is guarded to run once (inner panes keep
the existing re-apply behaviour, which restores the persisted position).
Alternative: persist the outer position and re-apply it like the inner
panes — deferred with the rest of persistence (Non-Goals).

**D4. Guard the draw path against `offset is None`.** `_draw_func` and
`to_widget_coords` read `offset.x` unchecked; `to_image_coords` already
returns `(None, None)` for a `None` offset. The guard makes
`to_widget_coords` treat a `None` offset as (0, 0) and `_draw_func` skip
the image paint (background still rendered) when no offset exists. With
D1/D2 this state should not arise, but a displayed pixbuf must never
crash rendering — the bug report's "nothing is displayed" becomes
"background until an offset exists" in any residual edge case.

## Risks / Trade-offs

- [`do_size_allocate` fires during layout; re-running `zoom_to_box` inside
  it mutates zoom/offset properties which queue redraws] → Mitigation: the
  re-fit path only emits `zoom-changed`/`offset-changed` and
  `queue_draw()` when values actually change (existing setters already
  compare), so allocation storms settle; the regression test pumps the
  main loop and asserts stability.
- [Half-split default differs from GTK3's "child1 takes the rest"] →
  Accepted: consistent with the inner panes' existing default; the image
  zooms to fit either way. Users can drag the divider.
- [View-mode switch re-packs panes and re-allocates from 0] → Mitigation:
  D1's re-fit hook re-applies zoom-to-fit on the new allocation, so the
  image re-fits after every switch; covered by the regression test.
- [The 0x0-allocation early-return in `zoom_to_box` stays] → Deliberate:
  it prevents a divide-by-zero; D1 re-applies the fit on the first real
  allocation, which is exactly the recovery the guard's comment promised.

## Migration Plan

Single-branch change, applied via `/opsx-apply`. Task order:

1. Regression tests first (TDD): a real-layout test that presents a
   window, imports a page-shaped pixbuf, and asserts the view allocation
   is non-zero and the zoom/offset were fitted; plus a `do_size_allocate`
   re-fit test.
2. `ImageView.do_size_allocate` override (D1) and the `None`-offset guards
   (D4).
3. `_vpaned` initialisation in `_pack_viewer_tools` for all modes (D2,
   D3).
4. Full gate: `pytest`, `ruff`, `ty check .`; verify no new uncovered
   lines.

Rollback: revert the commit; no data or config migration involved.

## Open Questions

- None.
