# Tasks

## 1. Canvas: restore middle-click panning

- [x] 1.1 Add a delivery-guard test to `tests/test_7_canvas.py` that
      locates the Canvas's `Gtk.GestureClick` via `observe_controllers()`
      and asserts its `button` property is `0` (listen to any button);
      verify it fails (red) against `Canvas.__init__` as it stands.
- [x] 1.2 Change `Canvas.__init__` in `canvas.py` to construct the click
      gesture as `Gtk.GestureClick(button=0)`; run `pytest
      tests/test_7_canvas.py` and verify the new guard test (green) and
      the existing canvas tests all pass.

## 2. ImageView: restore middle-click panning in the combined tool

- [x] 2.1 Add the equivalent delivery-guard test to
      `tests/test_imageview.py` (the ImageView's `Gtk.GestureClick` must
      listen to any button); verify it fails (red) against
      `ImageView.__init__` as it stands.
- [x] 2.2 Change `ImageView.__init__` in `imageview.py` to construct the
      click gesture as `Gtk.GestureClick(button=0)`; run `pytest
      tests/test_imageview.py` and verify the new guard test (green) and
      the existing image view tests all pass.

## 3. Integration verification and quality gates

- [x] 3.1 Verify the restored behaviour end-to-end: a middle-button drag
      pans both the image view (combined move/select tool) and the OCR
      canvas, a primary-button drag still draws a selection, and the
      context menu still opens on the secondary button (use the event
      injection harness or a manual smoke test).
- [x] 3.2 Confirm the View menu wording in README.md (Pan and Select &
      Pan tools) already documents the restored panning exactly and needs
      no edit.
- [x] 3.3 Run the full quality gate and verify all green: `pytest` (with
      the coverage thresholds from pyproject.toml), `ruff format`,
      `ruff check`, and `ty check .` — with no newly uncovered lines
      outside `if TYPE_CHECKING:` imports.

## Workflow follow-up

- Once the change is approved, implement it with `/opsx-apply`.
- Archive the change with `/opsx-archive-change` after review and a
  passing suite, then verify the archived `image-view-tools` spec and
  that `openspec validate` still passes at the root.
