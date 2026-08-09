## Why

Page numbers are currently sparse: they are sorted but not necessarily
consecutive (gaps persist after the two-pass duplex workflow, deletions, or
blank-page removal), which is surprising to users and makes the number an
unreliable indicator of how many sides remain to be saved. The stored
`page_number` is also redundant — the `page_order` table already carries a
`row_id` that tracks the same sequence in lockstep.

## What Changes

- **BREAKING** Page numbers SHALL always be consecutive `1..n`, derived from
  list position, and SHALL NOT be stored. `page_order.page_number` is dropped;
  `row_id` becomes the sole order key and is renumbered on insert/delete.
- **BREAKING** Scan insertion becomes positional. Basic single-sided scanning
  appends pages `1..n`. The duplex reverse pass interleaves each scanned back
  immediately after its facing partner (insert-after), rather than assigning
  temporary numbers from the end.
- **BREAKING** Extended page numbering becomes "insert before page N" (with an
  optional position advance per subsequent scan) instead of start/increment
  number arithmetic.
- **BREAKING** The duplex rotation decision keys on the "side to scan" setting
  instead of page-number parity.
- **BREAKING** The Renumber dialog is removed. Editing the page-number column
  moves the page to the entered position. Drag-and-drop and copy/paste perform
  positional reordering.
- Loading a session saved by an older version renumbers its pages `1..n` in
  row order.
- `pages_possible` / `max_pages` logic shrinks to the only remaining bound:
  the reverse pass cannot exceed the number of scanned facing pages.

## Capabilities

### New Capabilities
- `page-numbering`: Page numbers are always consecutive `1..n`, derived from
  position rather than stored. Covers position-based insertion at scan time
  (append, duplex reverse interleave, extended insert-before), the side-based
  rotation decision, positional reordering (drag, paste, number-column edit),
  and renumbering of legacy sessions on load.

### Modified Capabilities
<!-- None: no existing spec describes page numbering or scan insertion. -->

## Impact

- `scantpaper/docthread.py` — `page_order` schema (drop `page_number`),
  `add_page`, `replace_page`, `delete_pages`, `clone_pages`,
  `page_number_table`, `_take_snapshot`, `_get_snapshot`, undo/redo.
- `scantpaper/basedocument.py` — `add_page`, `renumber`, `valid_renumber`,
  `pages_possible`, `index_for_page`, `_index2page_number`, paste/drag logic.
- `scantpaper/dialog/pagecontrols.py` — start/increment spinboxes, extended
  mode, sided/side controls.
- `scantpaper/dialog/renumber.py` — removed.
- `scantpaper/scan_menu_item_mixins.py` — rotation via side-to-scan; scan start.
- `scantpaper/dialog/sane.py` — scan() start/step usage.
- `scantpaper/print_operation.py` — page-range matching becomes positional.
- `scantpaper/savethread.py` — replace-page keeps position.
- `scantpaper/tests/` — renumber, pages_possible, pagecontrols, scan dialog,
  and docthread test coverage.
