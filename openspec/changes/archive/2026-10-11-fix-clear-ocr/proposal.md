# fix-clear-ocr

## Why

The "Edit → Clear OCR" action crashes with
`AttributeError: 'int' object has no attribute 'text_layer'`. In
`edit_menu_mixins.py` `clear_ocr()` mutates `self.slist.data[i][2].text_layer`,
but `data[i]` is a list-model row `[number, thumb, page_id]` whose `[2]`
element is a **page id**, not a `Page` object. Even ignoring the crash, the
current code mutates an in-memory value, never talks to the worker thread, so
it would neither persist to SQLite nor be undoable.

## What Changes

- Fix `clear_ocr()` in `src/scantpaper/edit_menu_mixins.py` so it no longer
  treats the page-list row as a `Page` object.
- Clear the OCR text layer of each selected page **through the worker thread**
  (`DocThread.set_text(..., "[]")`), so the edit is persisted to SQLite and
  recorded as an undoable document action.
- Rewrite `tests/test_edit_menu_mixins.py::test_clear_ocr` so it reflects the
  real `data[i] = [number, thumb, page_id]` model and asserts against the
  worker-thread call rather than direct in-memory mutation.
- Clear the displayed text canvas as part of the action, consistent with the
  existing `t_canvas.clear_text()` call.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `ocr-recognition`: Add a requirement covering the reverse of recognition —
  clearing an existing OCR text layer for selected pages through the worker
  thread, persisted and undoable, with the stored image unchanged. This
  extends the existing text-layer lifecycle already specified for recognition
  and for undo/redo of OCR output.

## Impact

- `src/scantpaper/edit_menu_mixins.py` — `clear_ocr()` implementation.
- `src/scantpaper/tests/test_edit_menu_mixins.py` — corrected unit test.
- Worker thread `DocThread` (`src/scantpaper/docthread.py`) is reused as-is via
  the existing `set_text` operation; no new thread API.
- No dependency changes; no user-visible translation changes.
