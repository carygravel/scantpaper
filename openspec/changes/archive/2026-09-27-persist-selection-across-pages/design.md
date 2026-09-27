## Context

See proposal.md (Why) and the delta specs for requirements.

The selection rectangle is stored in the page's full-resolution image
coordinates. `Selector` records it via `to_image_coords` (`imageview.py:274`)
and it is kept in sync with `settings["selection"]` through
`_view_selection_changed_callback` (`app_window.py:629`).

On a page change, `_page_selection_changed_callback` (`app_window.py:713`)
captures `view.get_selection()` and immediately re-applies it, but at that
moment `_display_image` (`session_mixins.py:263`) has only shown the small
thumbnail pixbuf (the full-resolution page loads asynchronously via
`_on_page_loaded`). `ImageView.set_selection` (`imageview.py:900`) clamps the
selection against `get_pixbuf_size()` — the thumbnail — so a selection whose
origin lies beyond the thumbnail's size becomes degenerate (negative
width/height). `draw()` then skips it (`imageview.py:606`), so it is not
rendered. Because `set_selection` emits `selection-changed`, the degenerate
value is also written back into `settings["selection"]`, corrupting the value
used by the crop tool.

## Goals / Non-Goals

**Goals:**
- Keep the selection visible and correctly bounded when navigating between
  pages.
- Ensure the persisted `settings["selection"]` is never overwritten with a
  degenerate (thumbnail-clamped) rectangle.

**Non-Goals:**
- Independent per-page selections — a single shared selection rectangle is
  retained (matching the current config model and gscan2pdf's behaviour).
- Changing the crop tool or the selection storage format.

## Decisions

### Decision: Re-apply the selection after the full-resolution page loads
Move the re-application of the selection out of
`_page_selection_changed_callback` (where the pixbuf is still the thumbnail)
and into `_on_page_loaded` (`session_mixins.py`), immediately after the
full-resolution pixbuf is set. There, `set_selection` clamps against the
real image size, producing a valid, drawable rectangle and re-emitting the
correct value to `settings["selection"]`.

- Rationale: `set_selection` only has access to the currently displayed
  pixbuf, so it must be called when that pixbuf is the full-resolution image,
  not the transient thumbnail. This is the minimal change that makes the
  selection valid and non-corrupting.
- Alternative considered: teaching `set_selection` the full-resolution size
  independently of the displayed pixbuf — more invasive and not needed, since
  the full-resolution pixbuf is the natural clamp target at `_on_page_loaded`.

### Decision: Stop re-applying the selection against the thumbnail
Remove the `if sel is not None: self.view.set_selection(sel)` block from
`_page_selection_changed_callback`. This block is the direct cause of both
the degenerate display and the `settings["selection"]` corruption.

- Rationale: the selection is in full-resolution image coordinates and is only
  meaningful once a full-resolution page is shown; re-applying it to a
  thumbnail-only state is what degrades it.

### Decision: `_on_page_loaded` reapplies from `settings["selection"]`
`_on_page_loaded` re-applies `self.settings["selection"]` (when set) via
`view.set_selection`. Using `settings["selection"]` as the single source of
truth keeps the reapply consistent with the value the crop tool reads, and a
selection from a differently-sized page is clamped to the new page's bounds.

- Rationale: `settings["selection"]` is already kept in sync when the user
  draws; reading from it avoids relying on the transient view state.

## Risks / Trade-offs

- **Transient thumbnail flash** → for the brief moment a page shows only its
  thumbnail, the previously drawn selection is not re-applied until the
  full-resolution image loads; it then appears correctly. This is a minor,
  frame-level trade-off and is the price of never clamping against the
  thumbnail.
- **Selection carried between differently-sized pages** → the shared rectangle
  in image coordinates is clamped to each page's bounds on display, which is
  the intended preview behaviour; it is not re-projected proportionally
  (out of scope).
- **No selection present** → `_on_page_loaded` guards on
  `settings["selection"]` being set, so pages without a selection are
  unaffected.

## Migration Plan

No schema or persisted-state migration. Existing session files and configs
(including any `settings["selection"]` values) remain valid.

## Open Questions

None — the approach, specs, and task breakdown are unaffected by any
deferrable unknown.
