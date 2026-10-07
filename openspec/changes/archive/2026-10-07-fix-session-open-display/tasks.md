## 1. Regression tests (TDD)

- [x] 1.1 Model-level test: opening a session through the import flow
  (`open_session(..., finished_callback=cb)` with `finished_callback`
  forwarded the way `_get_file_info_finished_callback2` does for a session
  file) invokes `cb` after the page table is populated and page 0 is
  selected. Use the existing `Document` + worker-thread harness and the
  `mainloop_with_timeout` fixture (see `get_page_sync` in conftest.py).
- [x] 1.2 Window-level test: after a saved session is opened via
  `_import_files`/`import_files`, `_suppress_full_display` is `False` and a
  full-resolution page load (`_on_page_loaded`) runs, producing the pixbuf
  and the text layer, and page switches afterwards also load full-res. Follow
  the existing frontend test harness (test_0821_frontend_image_sane.py).

## 2. Implementation

- [x] 2.1 In `BaseDocument.open_session` (basedocument.py), inside `on_table`
  after `self.select(0)`, invoke `kwargs.get("finished_callback")` when
  present, passing `None`, so the File → Open import flow finalises (clear
  `_suppress_full_display`, finish progress, display the selected page).
- [x] 2.2 Widen `_import_files_finished_callback`'s parameter type
  (file_menu_mixins.py) to `Response | None` so the `None` completion signal
  from the session-open path is type-clean.

## 3. Verification & docs

- [x] 3.1 Run `pytest` (full suite passes; no new uncovered/partially
  covered lines), `ruff format`/`ruff check`, and `ty check .` — all clean.
- [x] 3.2 Update README.md if there is a user-visible behaviour section that
  should mention that opening a saved session now displays the full
  resolution page and its text layer.