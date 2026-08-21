## Context

The document of record lives in `DocThread`'s SQLite session: `page_order` rows
keyed by `action_id`, with every mutating operation copying the current rows
forward via `_take_snapshot()` (docthread.py:643). Undo/redo walk this chain by
decrementing/incrementing `_action_id`. Ordinary page deletion already goes
through this machinery: `Document.delete_selection()` (basedocument.py:407-430)
collects `page_ids` from the selected rows, sends `"delete_pages"`, and removes
the GTK model rows inside the `data_callback` when the thread replies with
`{"type": "page", "remove": row_ids}` (produced by `DocThread.do_delete_pages`,
docthread.py:479).

`FileMenuMixins.new_()` (file_menu_mixins.py:92) is the one mutation that
bypasses all of this: it assigns `slist.data = []`, which only clears the GTK
`ListStore` (simplelist.py:139). See proposal.md for the resulting desync and
issue #74 reproduction.

## Goals / Non-Goals

**Goals:**

- Make "New File" indistinguishable, from the snapshot chain's point of view,
  from deleting every page via the Edit menu.
- Reuse the existing, tested delete path rather than inventing a new message.
- Keep the existing UX guards (unsaved-changes prompt) and view-reset behaviour.

**Non-Goals:**

- Purging orphaned `page`/`image` rows from the session database (existing TODO
  at docthread.py:684; unchanged by this fix).
- Changing undo depth limits or redo semantics.
- Making document open/import symmetric (separate concern, not reported broken).

## Decisions

### D1: Reuse `delete_pages` instead of a new "clear" message

`new_()` will collect the `initial_page_id`s of all rows in `slist.data` and
send the same `"delete_pages"` request used by `delete_selection()`, with all
page ids. A thin `Document.delete_all_pages()` (modelled on
`delete_selection()`) provides the entry point so the file menu does not talk
to the thread directly.

*Why not a dedicated `"clear_document"` message?* It would duplicate
`do_delete_pages` logic (snapshot, delete, renumber, response shape) for no
behavioural gain. The renumbering loop in `do_delete_pages` is O(n) either way.

*Why not delete by `row_ids`?* `page_ids` (`initial_page_id`) are what
`delete_selection()` already sends and what the response/callback plumbing is
tested against (test_basedocument.py:821); reusing them keeps one code path.

### D2: Frontend updates stay callback-driven

The GTK model rows are removed in the `data_callback`, exactly as
`delete_selection()` does today - not synchronously before the request. The
thread serialises requests, so any scan queued after "New File" is applied to
an already-cleared snapshot chain. The historical race noted at
file_menu_mixins.py:99 (v2.5.5) is respected by keeping the existing
signal-blocking pattern around model mutation.

View state (image view pixbuf, canvas text, `_current_page`, selection) is
reset immediately in `new_()` as today; waiting for the callback would show
stale content for the round-trip duration and buys nothing, since the deleted
pages' thumbnails disappear on callback anyway.

### D3: Empty-document short-circuit

If `slist.data` is empty, `new_()` returns without sending a request. This
prevents an empty undo step (a snapshot identical to its predecessor) from
being recorded, satisfying the no-op requirement and keeping
`can_undo()`/`can_redo()` meaningful.

### D4: Undoable clear is accepted, documented behaviour

Undo immediately after "New File" restores the cleared pages. This falls out of
D1 for free and matches the semantics users already get from "delete all pages
then undo". It is a deliberate, documented change (README) - previously undo
after "New File" was enabled but semantically meaningless.

## Risks / Trade-offs

- [Async window between request and callback] → The thread queue is FIFO and
  the guard prompt runs before dispatch; the only visible effect is thumbnails
  persisting for the round-trip (milliseconds, same as ordinary deletion).
  Regression test asserts final state, not intermediate UI.
- [`new_()` previously synchronous, tests mock `slist.data = []`] → Existing
  tests in test_file_menu_mixins.py assert the old direct-clear behaviour and
  will be updated to assert the dispatched request + callback-driven clear.
- [Very large documents: one request carrying all page ids] → Same order of
  magnitude as selecting-all then deleting, which is already possible today;
  no new scaling behaviour introduced.
- [Session files created before this change] → No schema change; old sessions
  load unchanged since the fix only alters which requests are sent.

## Migration Plan

Pure code change, no data migration. Rollback is reverting the commit; session
databases written after the change remain valid because the on-disk format is
untouched.
