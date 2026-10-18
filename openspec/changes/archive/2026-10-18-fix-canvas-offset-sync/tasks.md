## 1. Regression tests (TDD)

- [x] 1.1 Real-layout test in `src/scantpaper/tests/test_canvas.py`:
      with a known page extent on an unmapped canvas, `set_offset(357, 0)`
      is stored unclamped; after presentation and first allocation the
      offset is clamped against the live allocation (currently fails:
      it collapses to (0, 0))
- [x] 1.2 Real-layout test: canvas shown after being hidden aligns with
      the image view — build the window (real builder, real ImageView),
      load a page, switch to the text-layer tab, and assert the canvas
      zoom/offset place the page where the view had it
- [x] 1.3 Real-layout test: shrink the window while the canvas is
      hidden, then show the canvas, and assert the page is still
      visible (offset re-clamped against the live allocation)
- [x] 1.4 Unit test: the deferred clamp emits `offset-changed` exactly
      once on the allocation that changes the offset, and nothing when
      the clamped value is unchanged

## 2. Canvas fixes

- [x] 2.1 In `src/scantpaper/canvas.py`, defer clamping in the offset
      setter while `get_allocation()` is zero-sized: after the existing
      no-extent guard, store the pushed value unclamped and return
      without emitting
- [x] 2.2 Add a `do_size_allocate` override that chains up, re-clamps
      the stored offset against the new allocation, and emits
      `offset-changed`/`queue_draw()` only on an actual change

## 3. ImageView symmetry

- [x] 3.1 In `src/scantpaper/imageview.py`, apply the same
      unusable-allocation guard to the `offset` setter: store unclamped
      when the allocation is zero-sized, re-clamp in
      `do_size_allocate`

## 4. Split pane minimums and position clamp

- [x] 4.1 Regression test: restore a saved inner-pane position larger
      than the pane (user's config: `split panel v` 278 in a 279px
      pane) and assert the canvas pane is still visible (≥ 100px)
- [x] 4.2 Give `ImageView` and `Canvas` minimum content sizes (100x100)
      so no pane can collapse to invisibility
- [x] 4.3 Clamp the restored saved position in `_init_split_pane` into
      `[handle + child1_min, size - handle - child2_min]`, measured at
      tick time

## 5. Gate

- [x] 5.1 Full suite: `pytest` passes with coverage thresholds met and
      no worse uncovered/partially-covered line counts
- [x] 5.2 `ruff check`, `ruff format --check`, and `ty check .` are
      clean
- [x] 5.3 Verify under xvfb with real OCR: after OCR, switching to the
      text-layer and annotation tabs shows the same page region as the
      image view; resize + tab switch keeps the page visible; a stale
      saved split position no longer collapses the canvas pane
