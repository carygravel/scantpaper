# Design: Adaptive filter quality — FAST during interaction, GOOD on idle

## Context

See proposal.md for motivation. Key measured facts: at fullscreen-A4 fit zoom
(~0.31×) `FILTER_FAST` renders in ~10 ms (~90 fps), `FILTER_GOOD` in ~47 ms
(~21 fps), `FILTER_BEST` in ~345 ms (~3 fps). The current implementation in
`ImageView._get_adaptive_filter()` picks a filter purely from zoom level (FAST
below 0.5×, GOOD below 1.0×, else the configured interpolation), which gives
point-sampled output exactly in the full-page view users rely on to judge
quality, while ignoring the user's configured interpolation below 1.0×.

The widget is `scantpaper/imageview.py`, a `Gtk.DrawingArea` port of the old
GtkImageView. Interaction flows through `Tool` subclasses (`Dragger` pans via
`set_offset`, `Selector` draws a rubber band) and `do_scroll_event` for zoom.

## Goals / Non-Goals

**Goals:**
- Static pages always render with the configured interpolation (default GOOD),
  independent of zoom.
- Interaction (pan, scroll-zoom) renders with FAST for responsiveness.
- Idle returns to GOOD automatically, without user action.

**Non-Goals:**
- Changing how pages are saved or exported (PDF/DjVu filtering is unaffected).
- Introducing mipmap/pre-downscaling caching (a possible future improvement,
  tracked separately; this change does not add the caching machinery).
- Exposing a user preference UI for interpolation (the `interpolation` property
  and its default GOOD are honoured as-is; wiring a settings toggle is out of
  scope).

## Decisions

**Decision 1: Replace zoom thresholds with interaction state.**
`_get_adaptive_filter()` returns `FILTER_FAST` while the view reports it is
interacting, otherwise the user's `interpolation`. This is zoom-independent, so
full-page fit and zoomed views both get GOOD when static.

**Decision 2: Interaction is a view-level flag driven by existing handlers.**
Add `set_interacting(bool)` (or an equivalent internal flag) on `ImageView`:
- `Dragger.button_pressed()` sets it True; `button_released()` sets it False.
- `do_scroll_event()` sets it True and (re)arms a short idle timeout
  (`GLib.timeout_add`, ~150 ms) that clears it when the scroll burst stops.
Rationale: these are the only paths that change offset/zoom and thus benefit
from FAST. `Selector` rubber-band dragging does *not* change offset/zoom, so it
is deliberately excluded — dropping to FAST there would blur the selection view
for no perf gain.

Alternative considered: keying off `self.get_tool().dragging` in the draw path.
Rejected because it couples the draw path to tool internals and can't express
the scroll case (which has no `dragging`).

**Decision 3: Clear the flag on an idle timeout for scroll, on button-release
for pan.**
Pan has a definite end (button release) and its own redraw via `set_offset`, so
release simply clears the flag. Scroll is a burst of discrete events with no
clean end; a short timeout (reset on each event) is the standard way to detect
"scroll stopped". Both paths call `queue_draw()` after clearing so the GOOD
repaint is scheduled. The surface cache (`_get_or_create_surface`) is unchanged,
so the GOOD repaint after idle costs one ~47 ms paint — the same cost the view
already pays today when zooming past 1.0×.

**Decision 4: Filter choice lives entirely in `_get_adaptive_filter()`.**
No changes to `do_draw` beyond what already exists. This keeps the change
minimal and keeps the existing `set_interpolation()`/property contract intact.

## Risks / Trade-offs

- **[Idle repaint latency]** After a pan/scroll ends, the GOOD re-render takes
  ~47 ms, a single visible frame tick. → Mitigation: this equals today's
  behaviour when crossing a zoom threshold, and it is a one-off after
  interaction, not per-frame. Acceptable.
- **[Scroll timeout mis-tunes]** If 150 ms is too short, FAST flickers on
  during a slow scroll; too long, GOOD appears late after stopping. → The value
  is a single constant, easy to tune; pick a conservative default and note it.
- **[Selector exclusion]** If a future tool reuses Dragger semantics for
  manipulation, FAST may apply inappropriately. → Gate on the specific
  offset/zoom-changing tools and document the intent.
- **[Behaviour regression risk]** Existing tests assert the zoom-threshold
  behaviour. → Update `test_adaptive_filter` to assert interaction-driven
  selection; add coverage for the idle-return and scroll-timeout paths.

## Migration Plan

Single-file change in `imageview.py`; no schema, data, or dependency changes.
Rollback is a one-line revert of `_get_adaptive_filter()` and the interaction
flag wiring.

## Open Questions

- Exact scroll-idle timeout value (150 ms is a starting point) — verifiable by
  eye during testing without changing specs.
- Whether panning is fast enough at GOOD on a real 4K/HiDPI display to question
  the FAST-on-pan choice — measurable in the implementation spike; the design
  is unchanged either way.
