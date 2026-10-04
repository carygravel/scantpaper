## Context

See `proposal.md` — Why, for the motivation. This section covers only the state
of the code that shapes the approach.

A layer being edited (text layer or annotations) exists in three structures at
once, all reachable from `Canvas`:

```
  Bbox tree                       serialised by hocr()
  Canvas._root_item                     │
   └ _CanvasRoot.children               ▼
     └ Bbox.children            page.text_layer ──► savethread ──► PDF
       (append-only)                    ▲
       ▲                               │
       │ get_children() returns         │ nothing writes here
       │ a throwaway copy               │ on delete
       │                                │
  ┌────┴──────────┐          ┌─────────┴──────────┐
  │ confidence    │          │ position index     │
  │ index         │          │                    │
  │ ListIter.list │          │ TreeIter           │
  │ [[bbox,conf]] │          │ ._bbox / ._iter    │
  │ asc by conf   │          │ root → cursor      │
  └───────────────┘          └────────────────────┘
     navigation only             navigation only
```

`_commit` in `layer.py` serialises the **tree** (`Canvas.hocr()` walks it) and
writes that to `page.text_layer`, which `savethread` then embeds. Navigation
reads the **two indices**. So the tree is the serialisation source of truth and
the indices are the interaction source of truth — and today only the indices
are actually mutated.

Three facts constrain the fix:

- `Bbox.__init__` appends to `parent.children`; `Bbox.get_children()` returns
  `isinstance`-filtered *copies*. The filter is vestigial — it dates from the
  removed GooCanvas scene, where `children` also held drawing items (see the
  comment at `tests/test_7_canvas.py:847`). Every mutation routed through
  `get_children()` is therefore a silent no-op: `delete_box`
  (`canvas.py:367`) and the sibling reorder in `update_box` (`canvas.py:339`).
  `_CanvasRoot.get_children()` returns the live list, which is why the
  annotation layer's *first* level behaves differently from deeper levels.
- `ListIter.list` is a real list and `remove_current_box_from_index` does mutate
  it, so confidence navigation happens to work. This is why the defect presents
  as "it looks deleted but it isn't".
- `Bbox.pango_layout` is cached on the model and read in `_draw_bbox`
  (`canvas.py:811`) with a single `is None` invalidation point, while
  `confidence2color()` is recomputed every frame. Colour tracks state; glyphs
  do not.

The existing specs already state the intended behaviour
(`openspec/specs/canvas-widget/spec.md`: "the bbox SHALL be removed from the
scene graph"), so this is an implementation-conformance change, not a behaviour
invention. The gap was untestability: `tests/test_7_canvas.py` asserts on
navigation and `tests/test_layer.py` asserts on mock call counts, neither of
which can observe tree membership or `hocr()` content.

## Goals / Non-Goals

**Goals:**

- One owner for structural change to the scene graph, so the tree, both indices
  and the serialised output cannot drift apart.
- Every guarantee in the specs to be observable from `canvas.hocr()` and from
  scene-graph membership, so a regression fails a test rather than a user's
  PDF.
- A repaint path that cannot serve stale text.

**Non-Goals:**

- Undo/redo for slice edits. `ocr-recognition` covers undoing the OCR
  *operation*; slice edits are a separate mechanism and a separate change.
- Line-vs-word click granularity. `get_bbox_at` returns a word's parent for
  `add_box`, while a click returns the deepest box; unchanged here.
- Performance work on `hocr()` serialisation. It is O(n) already and the edit
  path calls it once per commit.

## Decisions

### D1: The scene graph is the single source of truth; `Canvas` owns all
structural mutation

`Bbox` will no longer reach into `Canvas` to maintain indices. Instead the
mutation entry points live on `Canvas`, which owns the tree and both indices and
can repair them together:

```
Canvas.update_word(bbox, text, selection)  # data + both indices
Canvas.delete_word(bbox)                  # detach + both indices + prune
Canvas.add_word(...)                       # insert + both indices
```

`Bbox` keeps only data and pure derivation (`to_hocr`, `get_centroid`,
`confidence2color`). `Bbox.delete_box` / `Bbox.update_box` either go away or
become thin, side-effect-free data setters that `Canvas` calls.

*Why:* the drift is not caused by one bad line; it is caused by three
structures with no shared owner, each mutated by whoever happens to hold a
reference. The `get_children()` copy is the symptom that happened to be
reachable. Fixing only the copy leaves the next mutation free to drift again —
and indeed `update_box`'s position reorder is broken by the same copy, which
nothing has reported yet.

*Alternatives considered:*

- *Return the live list from `get_children()`.* One line, makes both existing
  mutations work. Rejected: it fixes the two known call sites and leaves the
  ownership inversion intact, so a third call site reintroduces the bug. It
  also cannot express "repair both indices after a structural change", which is
  the position-order defect.
- *Serialise and re-parse after every edit (tree as a pure view of hOCR).*
  Guarantees consistency by construction and would have hidden this class of bug
  entirely. Rejected: it destroys object identity, which both indices are built
  from, so every commit would need a full index rebuild and a thread round-trip
  to reparse — a visible latency regression on a per-OK action.
- *A `detach()` method on `Bbox`.* Better containment than exposing the live
  list, but still leaves each caller responsible for index repair. Retained as a
  *component* of D1 (see D2), not as the whole answer.

### D2: Children are exposed read-only; mutation goes through an explicit detach

`get_children()` will return the live list (the filter is dropped — `children`
only ever holds `Bbox` since the scene rewrite) so iteration and length checks
stop allocating, and `Bbox` gains an explicit `detach_from_parent()` that
removes itself from `self.parent.children` by identity. The live list is
returned rather than a defensive copy because the alternative — a copy plus a
separate mutator — reintroduces exactly the ambiguity that caused this bug:
two ways to address the same collection, one of which silently does nothing.

*Why explicit rather than `parent.get_children().remove(self)`:* identity-based
removal, immune to the `__eq__`-on-bbox question, and greppable.

### D3: Index repair is defined per order, not opportunistically

Today `delete_box` pops the confidence index at whatever `ListIter.index`
happens to be and separately nudges the `TreeIter` — regardless of which order
is active. `LayerEditor.edit` sets only the *active* index, so the other one
drifts.

New rule: after a structural change the Canvas re-establishes the cursor for
**both** orders from the surviving set.

- Confidence order: `ListIter` gains a removal by *identity*, not by
  `self.index`. Identity removal removes the "must not pop a stale index"
  fragility at the source, and the cursor is then clamped to the neighbour that
  was at or after the removed position (forward preference, matching current
  behaviour).
- Position order: the `TreeIter` is **rebuilt** from the next surviving word in
  reading order (or the previous one if there is no next). Rebuilding is cheap
  and is the only thing that is correct after a removal, because a `TreeIter`
  holds a cached index path whose ordinals are invalidated by the removal.

*Why not keep the current "advance both" approach:* it works only in the order
that happens to be active, and the inactive order silently accumulates
references to deleted words — which is how the deleted word stayed reachable
after a deletion in position order.

### D4: `update_box` no longer implies delete

The empty-text case is currently an `if len(text) > 0: ... else: delete_box()`
branch, which couples a data setter to a structural mutation.
`Canvas.update_word` will never delete. `LayerEditor.ok` decides: empty text
means delete, and it does so through the same `delete_word` path the Delete
button uses, then moves the editor on. A setter that silently destroys its
argument is the reason "select all, press Delete, accept" gave no feedback — the
text was interpreted as an instruction, and the instruction was broken.

*Consequence for the specs:* the "Delete box when text is empty" scenario in
`canvas-widget` is retained (the user-visible behaviour is unchanged) but is
now driven by the editor, not by `update_box`.

### D5: Empty ancestors are pruned at deletion time, reusing the import-time
rule

`bboxtree._prune_empty_branches` already encodes "a node with neither text nor
descendants is not content" — but it only runs on parse. Deleting the last word
of a line would otherwise leave `<span class='ocr_line' …>\n</span>` in the
saved hOCR, and the in-memory tree would disagree with the tree rebuilt on the
next load.

The rule is expressed once as a predicate and applied both on parse and on
delete, so the two paths cannot diverge. It walks *up* from the deleted word
only, not the whole tree — deletion is local, and a full prune per keystroke-OK
is wasted work.

The root page box is exempt: it carries the page geometry that
`hocr()`/`to_djvu_txt` need.

*Why not serialise-then-reparse to canonicalise:* see D1's rejected
serialise/reparse; same identity cost, plus a thread round-trip.

### D6: Text-layout caching moves out of the model, and is keyed on the text

Two candidate fixes for the stale glyphs:

1. Set `bbox.pango_layout = None` in `update_box`.
2. Stop caching on the model; keep a per-frame layout map on the Canvas.

(1) is the smaller diff but leaves the layering violation: a `Pango.Layout` is
created from a `cairo.Context` in `_draw_bbox` and stored on the scene-graph
node, so the model holds a handle to a drawing-time object. Any future path that
mutates text without going through `update_box` reintroduces the bug — which is
the same failure mode as D1, one layer down.

Choose (2): the cache lives on the Canvas, never on the Bbox. Correctness then
does not depend on invalidation discipline at all.

The cache is keyed on `(bbox, text, font description)` rather than on `bbox`
alone, which is what makes the stale-glyph bug impossible without an invalidation
hook: a corrected word's text is part of a different key, so it is re-laid-out,
while an unchanged word still hits the cache. `Canvas.delete_word` drops the
deleted box's entries so a long editing session does not accumulate them.

*Profiling outcome.* A strictly per-frame map was measured on a synthetic
1200-word page (60 lines x 20 words) and cost **103.7 ms/frame** against the old
per-Bbox cache's **55.8 ms/frame** — a 1.86x regression on every zoom, pan and
resize, because each redraw re-created every layout. Keying on the text as well
keeps the cache across frames and brings it to **57.7 ms/frame**, within ~3% of
the old figure, with zero layouts rebuilt on steady frames. So the cross-frame
keyed cache is the implemented variant, and the per-frame map is not.

### D7: The editor treats "no current slice" as a normal state

`LayerEditor.delete` currently ends with `edit(self.canvas.get_current_bbox())`,
and `ListIter.get_current_bbox` raises `StopIteration` when the list is empty —
so deleting the last slice is an unhandled crash path. `edit(None)` is already a
no-op that logs; the editor will instead clear the control and leave navigation
controls inert.

`LayerEditor.ok` must also stop re-focusing `_current_bbox` after a delete. The
editor tracks a cursor it is allowed to move, and a delete clears it rather than
leaving it aimed at a detached box — which is the precondition for the
"never offers a slice that no longer exists" requirement.

### D8: Tests assert on serialised output, not on navigation

Every guarantee added in `specs/canvas-widget/spec.md` is expressed so that it
can be checked against `canvas.hocr()` and scene-graph membership. Navigation
assertions are kept only where navigation is the subject.

This is the part that actually prevents recurrence: the current tests pass
against code where deletion does nothing, because they assert that
`get_last_bbox` eventually raises. `tests/test_layer.py` must keep at least one
integration test that drives the real `LayerEditor` against a real `Canvas` (the
rest can stay mock-based), because a mock cannot observe a no-op mutation.

## Risks / Trade-offs

**Risk: `get_children()` returning the live list lets a future caller mutate the
tree by accident.** → Mitigation: every removal path in the new code goes
through `detach_from_parent` / `Canvas.delete_word`, and D1 puts those on
`Canvas`. The live list is what makes `remove` by identity expressible at all;
the alternative is a copy plus a mutator, which is the ambiguity being removed.

**Risk: rebuilding the position `TreeIter` on every delete costs a tree walk.**
→ Mitigation: `TreeIter.__init__` is a single parent-chain walk (depth ≈ 4).
Deleting is a deliberate user action, not a hot path. If a page ever needs bulk
deletion, the rebuild is hoisted to one rebuild at the end.

**Risk: pruning empties on delete removes a `page` box and breaks
`hocr()`/`to_djvu_txt` geometry.** → Mitigation: the root is explicitly exempt
(D5), and the canvas-widget delta carries a scenario asserting the page box
survives while words do not.

**Risk: making `update_box` non-deleting changes behaviour for any caller that
relied on the implicit delete.** → Mitigation: `layer.py` is the only caller,
and `LayerEditor.ok` implements the empty-text-means-delete rule explicitly
(D4). A test asserts the empty-OK path still deletes, so the user-visible
contract is pinned even though the mechanism moved.

**Risk: moving layout caching off the model regresses redraw performance on
large pages.** → Measured and resolved: the per-frame variant cost 1.86x on a
1200-word page, so the cache is retained across frames keyed on
`(bbox, text, font description)` (see D6), which costs ~3% and rebuilds nothing
on unchanged pages. Both cache lives are on `Canvas`, so no drawing-time object
is stored on a `Bbox`.

**Trade-off accepted:** D1 is a larger diff than the one-line `get_children`
fix, and touches `add`/`copy` paths that currently work. Accepted because the
one-line fix leaves two of three structures unowned, and because `add`/`copy`
already reach into `confidence_index` from `add_box` — the same inversion, so
they are in scope for consistency.

## Migration Plan

No data migration. The on-disk format, the saved PDF/DjVu shape, and the SQLite
schema are untouched; only which words end up in the serialised layer changes,
and only to match what the user already asked for.

Rollback is a plain revert. Sessions saved by the fixed version are ordinary
text layers — with the difference that a line whose words were all deleted is
absent rather than present-but-empty, which the pre-existing parser already
handles (`_prune_empty_branches`).

Regression guard: add a test that round-trips a page through
`Bboxtree.from_hocr(canvas.hocr())` and asserts the word count matches the
scene graph, so an existing session file cannot silently lose or gain words.

## Open Questions

- Whether `_prune_empty_branches` should move from `bboxtree` to a shared
  location once it has two callers. This affects file placement only, not the
  predicate, the specs, or the task breakdown — safe to settle while
  implementing.
- Whether the annotation layer needs the `copy` control at all (it is currently
  only enabled for the text layer). Behavioural, but explicitly unchanged here;
  worth a separate look if annotation editing grows.
