## 1. Selection clamp hardening (crop non-negative)

- [x] 1.1 Update `set_selection` in `src/scantpaper/imageview.py` to guard the
  clamp so it never yields a negative rectangle, keeping the in-place clamping
  that session_mixins relies on to bound the shared selection
- [x] 1.2 Guard the clamp arithmetic so width and height never go negative when
  a selection starts outside the image or exceeds the image bounds
- [x] 1.3 Add tests in `test_imageview.py` covering: negative-x clamp, negative-y
  clamp, selection larger than the image, and full out-of-bounds selection
  (result never has negative width/height)

## 2. Crop guard

- [x] 2.1 Validate `width` and `height` in `do_crop`
  (`src/scantpaper/docthread.py`) and reject non-positive dimensions with a
  clear error routed through the existing error path, without touching PIL
- [x] 2.2 Add tests in `test_docthread.py` covering: zero-width crop, negative
  width, negative height, and a valid crop still succeeding
- [x] 2.3 Add a test that a rejected crop does not change the page image

## 3. Phantom page reconciliation

- [x] 3.1 Add a reconciliation helper in `src/scantpaper/basedocument.py` to
  remove a stale page id from the frontend list and renumber consistently
  (reusing existing list-rewrite helpers)
- [x] 3.2 Update the `get_page` error path in `src/scantpaper/session_mixins.py`
  (`on_page_error` / `_on_page_loaded`) to reconcile the frontend list when the
  missing page is still referenced, instead of only logging
- [x] 3.3 Ensure the view is left in a consistent state (clear/redirect) after a
  page is reconciled away
- [x] 3.4 Add tests in `test_session_mixins.py` covering: stale page dropped,
  renumbering stays consistent, valid pages unaffected, and the error is not
  reported again on subsequent display

## 4. Specs and quality gates

- [x] 4.1 Confirm the delta spec scenarios are covered by the added tests
- [x] 4.2 Run `ruff format` and `ruff check` on changed files
- [x] 4.3 Run `ty check .` and keep it clean
- [x] 4.4 Run `pytest` and confirm coverage thresholds are met (no new
  uncovered lines beyond the `TYPE_CHECKING` imports)
