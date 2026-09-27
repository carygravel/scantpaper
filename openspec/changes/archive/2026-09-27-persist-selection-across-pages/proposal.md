## Why

A selection drawn on one page is not usable as a preview on other pages: when
the user navigates away and back, the selection rectangle is re-applied
against the small thumbnail that is displayed during the page change, which
clamps it to a degenerate size so it is not drawn at all. The selection
therefore appears to be forgotten, even though the intent (as in gscan2pdf)
is to keep it visible so the user can confirm a crop region lands correctly on
every page before applying it.

## What Changes

- A selection made on a page is kept visible and correctly placed when the
  user navigates to another page, instead of being clamped away against the
  transient thumbnail.
- The selection is re-applied (and validated) against the full-resolution page
  image rather than the thumbnail shown while a page loads.
- The drawn selection remains bounded within each displayed page's image area.

## Capabilities

### New Capabilities

- `selection-across-pages`: the selection rectangle persists and previews
  correctly when the user navigates between pages, bounded within each page's
  image area.

### Modified Capabilities

- `image-rendering`: the selection rectangle is re-applied against the
  full-resolution page (not the transient thumbnail), so it stays visible and
  correctly positioned across page changes.

## Impact

- `src/scantpaper/imageview.py`: `set_selection` clamping must not degrade a
  selection against a transient (thumbnail) pixbuf; the selection should be
  validated against the page's full-resolution image.
- `src/scantpaper/session_mixins.py`: `_on_page_loaded` re-applies the
  selection once the full-resolution page is displayed.
- `src/scantpaper/app_window.py`: `_page_selection_changed_callback` no longer
  re-applies the selection against the thumbnail-only state.
- Tests: `test_imageview.py` (clamping/rendering) and a test covering
  navigate-page-then-selection-is-visible.
