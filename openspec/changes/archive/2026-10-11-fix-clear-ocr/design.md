# fix-clear-ocr Design

## Context

`clear_ocr()` in `edit_menu_mixins.py` currently does
`self.slist.data[i][2].text_layer = None`. But `Document.data[i]` is a
list-model row `[number, thumb, page_id]`; `data[i][2]` is a **page id**, not
a `Page` object — hence the `AttributeError: 'int' object has no attribute
'text_layer'`. The action never talks to the worker thread, so it could not
persist or be undone even if it didn't crash.

See `proposal.md` for the motivation.

## Goals / Non-Goals

**Goals:**
- Make Clear OCR work without crashing, for one or many selected pages.
- Route the edit through the worker thread so it persists to SQLite and is
  undoable/redoable.
- Make a multi-page clear a single undo step, matching the existing
  multi-page edit pattern.
- Correct the unit test so it reflects the real `data[i]` row model.

**Non-Goals:**
- Changing the OCR *recognition* pipeline (only its inverse, clearing, is in
  scope).
- Introducing a new worker-thread operation or API.
- Changing the `ocr_flag`/`ocr_time` semantics of OCR'd pages (see Open
  Questions).

## Decisions

**Decision 1: Reuse the existing `set_text` worker operation to clear.**

The worker already has `set_text(page_id, text)` → `do_set_text` which takes a
snapshot (undoable) and versions the page (persisted). Passing the empty tree
`"[]"` clears the layer, because `Page` maps `"[]"` to `text_layer = None`
(`page.py:166`). This mirrors `LayerEditor._persist` (`layer.py:239`) which
uses the same setter.

- Alternative considered: mutating `Page.text_layer` directly (the old code) —
  rejected; it bypasses persistence, undo, and the row model.
- Alternative considered: a new dedicated `clear_ocr` worker op — rejected;
  `set_text` already provides exactly the required semantics (persist +
  undoable, image untouched), so a new op would be YAGNI.

**Decision 2: Batch multi-page clears into one undo step.**

Mirror the established pattern for multi-page edits in
`edit_menu_mixins.py:98-116` (`properties_apply_callback`) and
`tools_menu_mixins.py` rotate/crop: wrap the loop in
`self.slist.begin_undo_batch()` / `self.slist.end_undo_batch()`
(`Document.begin_undo_batch` → `thread.send("begin_batch")`, `document.py:405`),
so all selected pages share a single undo step via
`do_begin_batch`/`do_end_batch` (`docthread.py:1197`).

**Decision 3: Clear the displayed canvas immediately.**

Keep the existing `self.t_canvas.clear_text()` call so the on-screen OCR
overlay disappears at once; the persisted/undoable change follows through the
thread, consistent with the existing action.

**Decision 4: Rewrite `test_clear_ocr` against the real row model.**

The current test sets `slist.data = [[0, 0, page1]]` with `page1` a
`MagicMock`, encoding the false assumption that `data[i][2]` is a `Page`. The
rewritten test uses `data[i][2]` as a page id and asserts the worker-thread
`set_text("[]")` dispatch, plus `begin_undo_batch`/`end_undo_batch` bracketing
for the multi-page case.

## Risks / Trade-offs

- [Clearing via `set_text` does not touch `ocr_flag`/`ocr_time`] → Accepted
  by design (Option A): those flags are transient, in-memory values set during
  the OCR run and are not persisted in the `page` schema, so there is no
  stored state to reset. The core bug fix clears the text layer only.
- [Empty-selection edge case] → Mitigation: if no pages are selected the loop
  is a no-op; keep the guard so begin/end batch still balance in a `try/finally`.

## Migration Plan

No data migration or deployment concerns: this only changes how an existing
menu action behaves. Rollback is reverting the implementation change and its
test.

## Open Questions

None.
