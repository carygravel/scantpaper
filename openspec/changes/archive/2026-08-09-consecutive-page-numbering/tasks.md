## 1. Storage layer (`docthread.py`)

- [x] 1.1 Change the `page_order` CREATE TABLE to drop `page_number`
- [x] 1.2 Add a `do_open` migration: detect legacy schema (has `page_number`),
      rebuild the table without it preserving all `action_id` rows (undo
      history), and add a test loading a fixture with gaps + undo history
- [x] 1.3 Extract an insert-at-position-with-shift helper (reverse-order row_id
      updates, per design Decision 2) from `clone_pages`; add unit tests
- [x] 1.4 Rework thread `add_page(page, number=None)` → append or
      `add_page(page, insert_after=<uuid>)` using the shift helper; update
      tests (spec: Single-sided scanning appends, Extended mode inserts before
      a page)
- [x] 1.5 `replace_page` keeps the row's position; update tests
- [x] 1.6 `delete_pages` stops reading/writing `page_number` (row_id compaction
      already exists); update tests (spec: Deleting a page renumbers the
      remainder)
- [x] 1.7 `clone_pages` drops `page_number`; update tests
- [x] 1.8 `page_number_table` and `_get_snapshot` order by `row_id` and stop
      selecting `page_number`; update tests
- [x] 1.9 Remove `find_row_id_by_page_number` and
      `find_page_number_by_initial_id`
- [x] 1.10 `do_import_page` and `do_split_page`/`do_crop` pass `insert_after`
      instead of a computed number

## 2. In-memory document (`basedocument.py`, `simplelist.py`)

- [x] 2.1 `BaseDocument.add_page` mirrors append/insert-after and renumbers
      `self.data[i][0] = i+1`; update tests (spec: Page numbers are always
      consecutive)
- [x] 2.2 `_on_row_changed` moves the edited page to index (value-1) via the
      cut/paste clone path instead of sort+renumber; add tests (spec: Editing
      the number column moves a page)
- [x] 2.3 `paste_selection` renumbers positionally; update tests
- [x] 2.4 `renumber()` reduced to "set `self.data[i][0] = i+1`" or removed
      where unused
- [x] 2.5 Remove `pages_possible`, `index_for_page`, `valid_renumber`,
      `_index2page_number`
- [x] 2.6 `open_session` renumbers loaded pages 1..n in row order; add test
      with a legacy fixture (spec: Legacy sessions are renumbered on load)

## 3. Scan flow and dialogs

- [x] 3.1 Change the `new-scan` signal payload to `(image, insert_after, side,
      xres, yres)` and update `_new_scan_callback` to choose rotation from
      `side` instead of `page_number % 2`; add tests (spec: Duplex rotation
      follows the side being scanned)
- [x] 3.2 Basic single-sided scanning appends (remove start/increment from the
      simple path); update tests (spec: Single-sided scanning appends)
- [x] 3.3 Basic double-sided: track `batch_start`/`n` while facing; on reverse,
      insert each back after front `batch_start + n - k`; `max_pages = n`; add
      tests for full interleave and a mid-pass save (spec: Double-sided
      scanning interleaves reverse pages, Reverse pass is bounded by facing
      pages)
- [x] 3.4 Extended mode becomes "insert before page N" with position advance;
      update `pagecontrols.py` spinboxes and `dialog/sane.py` `scan()`; add
      tests (spec: Extended mode inserts before a page)
- [x] 3.5 Remove `pages_possible`/`max_pages` computation from the scan dialog
      apart from the reverse bound
- [x] 3.6 Confirm `scan_menu_item_mixins` side-switch/start logic matches the
      new model; update tests

## 4. Renumber dialog removal

- [x] 4.1 Delete `dialog/renumber.py` and its tests
- [x] 4.2 Remove the Edit-menu renumber item and `renumber_dialog` from
      `edit_menu_mixins.py`; update tests
- [x] 4.3 Remove renumber references in `app_window.py`/`session_mixins.py`;
      update tests

## 5. Save and print alignment

- [x] 5.1 Verify `print_operation.py` page-range matching is positional under
      the 1..n invariant; add/adjust test (spec: Page ranges refer to
      positions)
- [x] 5.2 Verify `savethread.py` `replace_page` position handling; update tests

## 6. Full verification

- [x] 6.1 `pytest` passes with coverage no lower than before the change
- [x] 6.2 `black` formatting applied
- [x] 6.3 `pylint` score no lower than before the change
