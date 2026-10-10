## Why

A user session produced two related, user-visible failures. After a scan the
frontend's page list held page ids (16-30) that no longer existed in the
database's current undo snapshot, so loading each one logged
`Page id N not found` over and over. Separately, applying a crop with a
non-positive width crashed with the opaque PIL error
`Coordinate 'right' is less than 'left'`. Both are cases where the UI state
drifts out of sync with the worker's authoritative state and fails with a hard
exception instead of degrading gracefully.

## What Changes

- **Phantom page reconciliation**: when `get_page` cannot find a page that the
  frontend list still references, the frontend SHALL reconcile itself (drop the
  phantom row / reload the current snapshot) instead of leaving a broken page in
  the list that errors on every display.
- **Crop guard**: `do_crop` SHALL reject (or clamp) non-positive crop width or
  height instead of passing them to PIL and crashing.
- **Selection clamp hardening**: `set_selection` SHALL NOT produce a negative
  width or height when clamping a selection to the image bounds, so the shared
  `settings["selection"]` object is never left with an invalid (negative)
  rectangle.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `selection-across-pages`: The selection clamp and the crop operation SHALL
  never yield a non-positive rectangle; cropping with an invalid selection SHALL
  be handled cleanly rather than crashing.
- `async-display-image`: A page load failure SHALL reconcile the frontend page
  list instead of merely logging an error and leaving a phantom page behind.

## Impact

- `src/scantpaper/docthread.py` — `get_page` (not-found reporting) and
  `do_crop` (guard against non-positive dimensions).
- `src/scantpaper/imageview.py` — `set_selection` clamp must not produce
  negative dimensions or mutate the caller's rectangle object destructively.
- `src/scantpaper/session_mixins.py` — `_display_image` / `_on_page_loaded`
  error path reconciles the frontend list on a not-found page.
- `src/scantpaper/basedocument.py` — reconciliation helper to remove a phantom
  row from the page list.
- Tests: extend `test_docthread.py`, `test_imageview.py`,
  `test_session_mixins.py`; update the affected spec scenarios.
- No dependency changes.
