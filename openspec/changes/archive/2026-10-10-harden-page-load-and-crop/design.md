## Context

See proposal.md - Why for the two motivating failures. Relevant current state:

- The document's authoritative page set lives in SQLite as a stack of undo
  snapshots keyed by `action_id` (`page_order`). `get_page` (docthread.py:663)
  resolves a page only against the current `action_id` and raises
  `ValueError("Page id N not found")` otherwise.
- The frontend page list (`self.data` in basedocument.py) is an independent,
  in-memory mirror of that page set. It is refreshed only on undo/redo
  snapshots and explicit add/remove events, so it can drift to hold stale page
  ids.
- `_display_image` (session_mixins.py:263) sends `get_page`; its error path
  (`on_page_error`, session_mixins.py:282) only logs, leaving the phantom row
  in place to error again on every display.
- `set_selection` (imageview.py:900) clamps a `Gdk.Rectangle` in place. When a
  selection starts outside the image or the image is smaller than the stored
  selection, the clamp can subtract the overshoot and produce a **negative**
  width/height. Because the same rectangle object is stored in
  `settings["selection"]`, the corruption persists.
- `do_crop` (docthread.py:1414) passes `width`/`height` straight to
  `PIL.Image.crop`, which raises the opaque
  `Coordinate 'right' is less than 'left'` on a negative width.

## Goals / Non-Goals

**Goals:**

- A stale page id in the frontend list resolves gracefully instead of flooding
  the log with `Page id N not found`.
- A crop with a non-positive width/height is rejected cleanly.
- Selection clamping never yields a negative rectangle and never corrupts the
  shared selection object.

**Non-Goals:**

- Diagnosing or fixing the underlying *cause* of the drift (e.g. interrupted
  scans or reopened-session staleness). Those are follow-ups; this change makes
  the system degrade gracefully.
- Changing how the worker reports `get_page` failures (the worker still raises
  `ValueError`; only the frontend response changes).

## Decisions

### 1. Reconcile on the frontend, keep the worker contract unchanged

`get_page` continues to raise `ValueError` on a missing page (that is spec'd in
`async-display-image` and relied on by tests). Reconciliation happens in the
frontend error path. When a not-found error arrives for a page that
`find_page_by_uuid` still references, the frontend removes that row and
renumbers (reusing the existing `_renumber_after_add` / list-rewrite helpers in
basedocument.py), then selects/clears the view as appropriate.

- *Alternative considered:* have `get_page` silently return a placeholder.
  Rejected - it would mask real data problems and hide the not-found condition
  the worker currently signals.

### 2. Guard `do_crop` against non-positive dimensions

`do_crop` validates `width` and `height` before touching PIL and reports a
clear, user-facing error (routed through the existing `error_callback`) instead
of a raw exception. This is defense in depth: even if a bad selection slips
through the clamp, it can no longer crash the worker.

- *Alternative considered:* clamping the crop to a minimum size in `do_crop`.
  Rejected - the user asked to crop a specific area; silently changing it is
  worse than rejecting the invalid selection.

### 3. Make `set_selection` non-negative while keeping in-place clamping

`set_selection` keeps its existing in-place clamping: session_mixins re-applies
the shared `settings["selection"]` through it on every page load, and the
in-place mutation is what keeps the stored selection bounded to the currently
displayed page. The fix is to guard the arithmetic so width/height never go
negative: a fully out-of-bounds selection clamps to zero area, never negative.
This keeps `settings["selection"]` valid at all times and is what feeds the
crop guard in decision 2.

- *Alternative considered:* operating on a local copy and not mutating the
  caller's rectangle. Rejected during implementation - the existing tests
  encode the mutation contract (imageview.py test at line 128-138) and, more
  importantly, session_mixins depends on `set_selection` clamping the shared
  `settings["selection"]` to the current page on each load. Removing the
  mutation would break that invariant and could reintroduce out-of-bounds
  crops.
- *Alternative considered:* normalizing the rectangle (swap coordinates so
  width/height are always positive) in the crop path. Rejected - the frontend's
  stored selection is shared and drawn by the canvas; fixing the clamp at its
  source is the correct single point of correction.

## Risks / Trade-offs

- [Phantom-page reconciliation removes a row the user can still see]
  → Removal is the correct action since the page genuinely no longer exists;
  the worker would never load it anyway. Renumbering keeps the list consistent.
- [Guarding `do_crop` could reject a crop the user intended]
  → A non-positive crop is meaningless; rejecting with a clear message is
  strictly better than the current crash.
- [`set_selection` normalization could mask genuine selection bugs]
  → The existing `selection-across-pages` spec already requires clamping; this
  only prevents the negative/zero-destructive edge cases.
