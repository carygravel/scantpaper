# Tasks

## 1. Message dialog layout

- [x] 1.1 Move the global hide label and checkbox out of the message grid into
  a fixed row appended to the content area after the scrolled window, and set
  the scrolled window to expand vertically. Verify the existing message,
  filtering, and stored-response tests still pass.
- [x] 1.2 Set the message grid's column and row spacing to
  `DIALOG_ROW_SPACING`. Verify the existing message, filtering, and
  stored-response tests still pass.
- [x] 1.3 Add structural tests asserting that the global label and checkbox
  are not descendants of the scrolled window, that their parent is the fixed
  row, and that the scrolled window requests vertical expansion.
- [x] 1.4 Add layout tests with one empty message and with several messages.
  Present the dialog at a known size and assert the global checkbox is mapped
  and ends above the action area, while the scrolled window is taller than its
  natural row height. Verify the tests pass under the project's wait-until
  helper.
- [x] 1.5 Add spacing tests asserting that the grid's column and row spacing
  equal `DIALOG_ROW_SPACING`, and that adjacent header cells have a non-zero
  gap after the dialog is presented.
- [x] 1.6 Add the user-visible dialog fix to `changelog.md`. Verify the entry
  describes the fixed control placement, the expanding message list, and the
  new column and row spacing.
- [x] 1.7 Show an empty Page cell when a message has no page number, instead
  of `None`, and test both unknown and known page numbers.

## 2. Dialog closing

- [x] 2.1 Replace the message `Gtk.TextView` with a selectable, wrapping
  `Gtk.Label`, and read stored responses with `get_text()` instead of from a
  text buffer. Remove the post-map relayout of the message list. Verify the
  existing message, filtering, and stored-response tests still pass.
- [x] 2.2 Return a close response and hide the dialog on Escape and on the
  window close control, so a caller waiting in `run_dialog()` returns.
- [x] 2.3 Add tests asserting that message text is selectable and that Escape
  and the close control both return a response and hide the dialog.
- [x] 2.4 Add the closing fix to `changelog.md`, including why the message text
  is no longer a focusable text view.

## 3. Integration verification

- [x] 3.1 Run `ruff format`, `ruff check`, `ty check .`, and `pytest`; confirm
  the coverage threshold passes and that no newly uncovered or partially
  covered lines were introduced outside type-only imports.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived specs and change status.
