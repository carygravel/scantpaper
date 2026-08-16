## Context

Importing a batch of files walks a chain of callbacks: `import_files`
(`document.py:44`) gathers file info, then `_get_file_info_finished_callback2`
fires `import_file` once per file (`document.py:131`). Each page arrives on the
main thread via `add_page` (`basedocument.py:231`), which always calls
`renumber()` (`:280`). `renumber()` (`:527`) loops over all rows and writes the
number column of each, so appending page `i` costs `i` model writes on the GUI
thread — O(n^2) for a batch.

The worker thread already returns a correct sequential position for appended
pages (`docthread.py:389-402`), so the number assigned to a new appended row is
already right and earlier rows are untouched.

## Goals / Non-Goals

**Goals:**
- Eliminate the per-page O(n) `renumber()` cost for the common append-in-order
  import path.
- Keep page numbers guaranteed consecutive 1..n after every operation
  (unchanged observable behavior).
- Add a single end-of-batch `renumber()` as a safety net for concurrent actions.

**Non-Goals:**
- Batching worker-side snapshots/undo steps (separate concern; changes undo
  granularity).
- Introducing model virtualization or lazy thumbnail loading.
- Changing the DB schema.

## Decisions

### D1: Skip the global rewrite when the appended number is already correct
In `add_page` (`basedocument.py:231`), `renumber()` is only required when rows
before the new row are affected — middle inserts (`insert-after`) and replaces
(`replace`), where positions shift — or when the appended row's number is not
already its position. For a plain append (`i is None`, `:250`), the worker
thread already passes a sequential position, so the appended row's number is
correct and no existing row moves.

Implement with an O(1) guard rather than skipping `renumber()` unconditionally:
- Middle insert / replace (`else` branch): always `renumber()` (positions shift).
- Append (`i is None`): skip `renumber()` only when `number == len(self.data)`
  (i.e. the appended value is already its 1-based position); otherwise fall back
  to `renumber()`.

Rationale: the guard preserves the existing correctness contract even if a
caller passes a non-sequential number on append (see `test_add_page_renumbers`,
which appends pages numbered `10` and expects `1,2`), while making the common
in-order append path O(1). Alternatives — a generic "defer renumber" flag or
removing renumber from append entirely — were rejected as more intrusive or as
breaking the out-of-order append guarantee.

### D2: One `renumber()` at end of a multi-file import
The batch finish path (`_get_file_info_finished_callback2_multiple_files`,
`document.py:87`) only attaches the real `finished_callback` to the last
`import_file` (`:128-129`). Add a `renumber()` call there so that, in the rare
case of a concurrent action during the batch, numbers are re-derived once.

Rationale: D1 makes per-page renumbering unnecessary for appends; D2 is a cheap
safety net. Because the finish callback is on the main thread, this single
O(n) pass is negligible compared to today's O(n^2).

### D3: Behavior contract preserved
Page numbers remain consecutive 1..n after every operation. The `page-numbering`
spec requirements are unaffected; this change only alters *when* `renumber()`
runs internally. Hence `skip_specs: true`.

## Risks / Trade-offs

- **Append vs. insert correctness**: D1 must correctly distinguish pure appends
  from middle inserts/replaces, and must keep the out-of-order append guarantee
  (`test_add_page_renumbers` appends numbered `10` and expects `1,2`). Existing
  tests for `insert_after`, `replace`, and out-of-order append guard against
  regressions.
- **Concurrent user action mid-batch**: D2's finish-callback `renumber()` covers
  this, but there is a brief window during the batch where numbering could be
  non-consecutive if the user acts mid-import. This is acceptable because the
  finish renumber restores order and matches current single-shot behavior at
  completion.
- **Other append callers**: scanning, `split_page`, `unpaper`, `user_defined`
  also append via `add_page` and will benefit from D1 without special handling.
