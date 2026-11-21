# Tasks

## 1. Drag icon

- [x] 1.1 Add unit tests in `src/scantpaper/tests/test_basedocument.py` for
  `_on_drag_begin`: a selected row with a pixbuf sets a thumbnail texture; no
  selection sets the transparent fallback; a selected row with no pixbuf sets
  the transparent fallback; a multi-selection uses the first selected row.
  Verify the new tests fail before the handler exists.
- [x] 1.2 Implement `_on_drag_begin` in `src/scantpaper/basedocument.py`,
  connect it to the drag source's `drag-begin` signal, and set the icon with
  `Gtk.DragSource.set_icon()` at hotspot `(0, 0)`. Verify the tests from 1.1
  pass.
- [x] 1.3 Document the visible change in the "Reorder by drag" README bullet
  and the unreleased changelog section. Verify both state that the drag icon
  shows the page thumbnail and never the internal payload text.

## 2. Integration verification

- [x] 2.1 Run the focused `test_basedocument.py` cases and the existing
  display-backed drag crash-gate tests. Verify all pass and the drag still
  reorders on drop.
- [x] 2.2 Run the full `pytest` suite and `python3 dev/check_test_coverage.py`.
  Verify the coverage gate passes with no new uncovered or partially covered
  lines.
- [x] 2.3 Run `ruff check .`, `ruff format --check .` and `ty check .`. Verify
  no diagnostics.
- [x] 2.4 Run the pinned OpenSpec 2.0.0 CLI with
  `validate --specs --strict --no-interactive` and
  `validate --archived --no-interactive`. Verify both pass.

## Workflow follow-up

- Sync the delta into `openspec/specs/page-reordering/spec.md`.
- Archive the change after review.
- Commit the change with the project's conventional commit message.
