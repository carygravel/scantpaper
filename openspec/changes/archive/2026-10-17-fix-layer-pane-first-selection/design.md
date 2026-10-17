# Design: fix-layer-pane-first-selection

## Context

See proposal.md for the problem statement. The relevant mechanics today:

- The canvas has exactly one notion of "known extent", `_pixbuf_size`
  (`get_pixbuf_size()`), and gates on it in three places: the selection drag
  (`canvas.py:1461`), scene drawing (`canvas.py:840`), and the offset clamp
  (`canvas.py:574`). It is set only by `set_text()` from the first bbox of a
  parsed layer (`canvas.py:794`) and reset to `None` by `clear_text()`.
- The gate never inspects layer *content* - it inspects the extent. The
  layer only ever supplied the extent, so on a page with no layer the extent
  is never learned and the gate stays shut: no drag, no rubber-band, no
  `selection-drawn`, Add stays disabled.
- Page display (`session_mixins._on_page_loaded`) already computes
  `page.get_size()` (line 277) and branches on the layer attribute:
  `create()` when truthy, `clear()` otherwise - two sentinels of "empty"
  (`None` and `"[]"`) both funnel into "extent never seeded" (`"[]"` takes
  `create()` -> `set_text([])` -> `StopIteration` return before line 794).
- The layer's own root bbox is built from `page.get_size()`
  (`layer.py:_new_layer_json`), so `page.get_size()` is already the
  canonical page extent in this code - the canvas was just never told it.

## Goals / Non-Goals

Goals:

- A page shown in a layer pane has a known extent whether or not it has
  layer content, for both the Text layer and Annotation editors.
- The fix holds for both empty-layer sentinels (`None` and `"[]"`).
- No behaviour change for pages that do have layer content: the final
  state after parsing is identical to today (the parse overwrites the
  seeded extent with the root bbox, exactly as today).

Non-Goals:

- Unifying the `None` vs `"[]"` empty-layer sentinels (thread 2).
- The pre-existing stale-root display bug (see Risks).
- Canvas zoom sync between panes (parity with the existing parse path,
  which syncs offset only).
- Renaming `_pixbuf_size` (legacy name, but `get_pixbuf_size()` is part of
  the `canvas-widget` spec contract).

## Decisions

### D1: Seed the extent at page load, from `page.get_size()`

`_on_page_loaded` calls a new `LayerEditor.set_extent(width, height,
offset)` for both editors *after* the existing create/clear branch, using
the `width, height` it already computes. `set_extent` delegates to a new
`Canvas.set_page_extent(width, height)` (sets the dict, queues a draw) and
applies `offset` via the existing `set_offset`.

Alternatives considered:

- **Seed inside `LayerEditor.create()`** - cleaner invariant ("create owns
  editor state"), but the no-layer branch of page load calls `clear()`, not
  `create()`, so `create()` alone misses exactly the pages we are fixing
  unless session is restructured to call `create()` unconditionally,
  which strands `clear()` (it has tests: `test_layer.py:695`).
- **Let the canvas read the extent from the ImageView** - couples the
  layer canvas to the image widget it is deliberately separate from.
- **A second state variable** (`_page_extent` beside `_pixbuf_size`) with a
  rewritten gate - two sources of truth for one concept; the gate condition
  (`extent is None`) is correct today, only its input was wrong.

Because the seed runs after the branch and `set_text` runs later (async
parse), the ordering is safe: content pages end with the parse's root-bbox
extent (identical to today); empty pages keep the seeded extent because
`set_text([])` returns before touching it.

### D2: The gate itself does not change

`_pixbuf_size is None` remains the gate for drags, drawing, and offset
clamping. The gate never checked for layer content, so the two tests that
lock it in (`test_draw_scene_pixbuf_none`,
`test_canvas_click_without_pixbuf_does_not_draw`) remain *correct and
unchanged*: no extent -> no draw. They become regression tests for the
"drag with no known page extent" scenario in the canvas-widget delta, and
a new test covers "extent known, no layer loaded" -> drag works.

This also means the "empty root + known extent" state is new: hit-testing
against an empty root already returns `None` safely (`_find_bbox_at`), and
the offset clamp now engages on layerless pages, which is desirable
(panning/zooming in the layer pane previously no-oped the offset).

### D3: `hocr()` is hardened against an empty root

`hocr()` gates on `get_pixbuf_size() is None` and then calls
`root.get_child(0)`, which raises `IndexError` on an empty root
(`_CanvasRoot.get_child` is a raw list index). Today the extent gate
happened to double as a "has content" guard; once the extent is known on
layerless pages it no longer is. Any future path that reaches `hocr()`
with no children (including deleting the last slice, if reachable) would
crash. The guard becomes: no extent **or** no children -> return `""`.

### D4: Sentinel-invariance falls out of D1

Nothing in the fix reads the layer attribute; the seed is unconditional
after the branch, so `None`, `"[]"`, and (later) any future representation
all get an extent. Thread 2 can then change the sentinel without
re-opening this bug.

## Risks / Trade-offs

- [Empty root + known extent makes `hocr()`'s empty case reachable] ->
  D3 hardens the guard; covered by a unit test.
- [Seeded extent vs parsed root-bbox extent could disagree] -> in
  practice both are `page.get_size()` (tesseract page bbox, pdftotext and
  `_new_layer_json` all use it); and on content pages the parse always
  wins last, so behaviour is identical to today.
- [Pre-existing: a page whose layer is `"[]"` takes `create()` ->
  `set_text([])` which returns *before* replacing the root, leaving the
  previous page's boxes displayed] -> not introduced or worsened by this
  change (that page could not draw before either, and now draws correctly
  on top of the stale display). Out of scope; recommend capturing it in
  the thread-2 change, where `set_text([])` should reset the root.
- [`set_extent` reaches into offset, which the clamp now honours on
  previously-unclamped states] -> applying the view's offset mirrors what
  the parse path already does (`on_parsed` -> `set_offset`), so the
  no-layer branch gains parity rather than divergence.
- [Session mock tests may need new expectations for `set_extent`] ->
  mechanical test updates; flagged in tasks.

## Migration Plan

None: client-side behaviour fix, no session/database format change, no
config change. Rollback is a plain revert.

## Open Questions

None - deferred items (sentinel unification, stale `"[]"` root) are
explicitly out of scope and belong to the separate thread-2 change.
