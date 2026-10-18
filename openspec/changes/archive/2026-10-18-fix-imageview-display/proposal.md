## Why

After the GTK3→GTK4 migration (e4e067a2), scanning or importing shows the
page's thumbnail in the thumbnail panel, but the page is never displayed in
the image view. Investigation verified two independent migration defects:

1. **The image view collapses to zero height.** `ImageView` is a bare
   `Gtk.DrawingArea` (minimum request 0x0). GTK3's `pack1(resize=True)`
   gave the notebook the leftover space (view allocated 697x491); GTK4's
   `Gtk.Paned` defaults its divider to child1's *minimum* request — just
   the 39px tab header — so the view is allocated 805x0 and paints nothing.
   The migration added `_init_split_pane` for exactly this collapse, but
   only wired it to the inner panes in split modes; the outer `_vpaned` is
   never position-initialised in any mode.
2. **The recovery path is dead code.** The migration replaced GTK3's
   `do_configure_event` with `connect("notify::width"/"notify::height",
   ...)` — but `GtkWidget` has no `width`/`height` properties in GTK4, so
   the handler that would re-run `zoom_to_box()` on the first real
   allocation never fires.

With both defects, `zoom_to_box()` early-returns on the 0x0 allocation,
`offset` stays `None`, and once the widget does get height (e.g. the user
drags the divider) the draw path raises
`AttributeError: 'NoneType' object has no attribute 'x'`. The display never
recovers, even manually.

## What Changes

- Initialise the outer `_vpaned` divider position in **all** viewer modes
  (tabbed, horizontal, vertical), extending the existing
  `_init_split_pane` approach so the image area is usable at startup.
- Replace the dead `notify::width`/`notify::height` handlers with a
  `do_size_allocate` vfunc override, so zoom-to-fit is recomputed whenever
  the allocation changes: first allocation, window resize, divider drag,
  and view-mode switch.
- Guard the draw path against a `None` offset so a displayed pixbuf can
  never crash rendering.
- Add regression coverage that exercises real allocation changes rather
  than mocked allocations.

## Capabilities

### New Capabilities
- `image-view-fitting`: The image view keeps the page fitted and visible
  across allocation changes (first allocation, window resize, divider
  drag, view-mode switch) and never renders a displayed pixbuf with an
  undefined offset.

### Modified Capabilities
- `view-layout`: The "split panes have a visible initial divider"
  requirement currently covers only horizontal/vertical split views. It is
  extended to all viewer modes including tabbed (the default), so the
  image area cannot collapse to zero height at startup or after a view
  switch.

## Impact

- Code: `src/scantpaper/imageview.py` (allocation handling, draw guard),
  `src/scantpaper/app_window.py` (pane initialisation in
  `_pack_viewer_tools`), and their tests.
- No dependency, data-model, or file-format changes; no session files
  affected.
- Repairs user-visible behaviour broken by the GTK4 migration; no
  intentional behaviour change beyond restoring GTK3 parity.
