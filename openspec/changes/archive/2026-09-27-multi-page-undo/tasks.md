## 1. Worker-thread batch mode

- [x] 1.1 Add an `_in_batch` flag to `DocThread` and make `_take_snapshot()` return early when it is set (so page ops inside a batch stop recording individual undo steps)
- [x] 1.2 Add `begin_batch` / `end_batch` thread requests (`do_begin_batch` / `do_end_batch` handlers); `do_begin_batch` calls `_take_snapshot()` exactly once then sets `_in_batch`, and `do_end_batch` clears it (see `design.md` — Decisions)
- [x] 1.3 Add unit tests in `test_docthread.py`: several page ops within one batch produce a single `action_id`; a batch of edits is undone in one step restoring every affected page; a batch is redone in one step re-applying every page; a single (non-batch) op still records one step

## 2. Frontend batch API

- [x] 2.1 Expose `begin_undo_batch()` / `end_undo_batch()` on `Document`/`BaseDocument` that forward `begin_batch` / `end_batch` to the thread via `send(...)`
- [x] 2.2 Add tests for the batch API forwarding and callback wiring (e.g. in `test_document.py`)

## 3. Batch the multi-page operations

- [x] 3.1 Wrap the `_rotate` page loop (`tools_menu_mixins.py`) in `begin_undo_batch` / `end_undo_batch` with `try/finally` so `end_undo_batch` always runs
- [x] 3.2 Wrap the `crop_selection` page loop (`tools_menu_mixins.py`) in the same batch pattern
- [x] 3.3 Add tests in `test_tool_menu_mixins.py` verifying that rotating and cropping multiple selected pages each yield one undo step and revert every page on undo

## 4. Quality gates

- [x] 4.1 Run `ruff format` and `ruff check` on changed files; fix any violations
- [x] 4.2 Run `ty check .` and fix any diagnostics
- [x] 4.3 Run the full `pytest` suite; confirm coverage thresholds are met and no uncovered lines are introduced outside `TYPE_CHECKING` imports
