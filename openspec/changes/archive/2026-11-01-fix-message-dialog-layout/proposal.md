# Proposal

## Why

The Messages dialog clips its global "Don't show this message again" label and
checkbox. Both are inside the scrolled message grid, which reports only its
first two rows of natural height, so the checkbox row is cut off even when the
dialog has unused height below the buttons. A user importing a file sees a
message they cannot read or acknowledge.

The read-only message text is a focusable `Gtk.TextView`, so closing the dialog
while the text has focus can segfault the GTK4 IBus input-method module when it
asks for the XID of a surface that is already gone. The dialog needs to close
safely with Escape and with the window close control as well.

## What Changes

- Move the global hide label and checkbox out of the scrolled message grid and
  into a fixed row below the message list and above the action buttons.
- Make the scrolled message list expand to the height the dialog allows, so it
  uses the surplus space instead of leaving it empty below the buttons.
- Set the message grid's column and row spacing to the existing
  `DIALOG_ROW_SPACING` value, so header labels, message cells, and hide
  checkboxes no longer touch.
- Keep the grid's column order and per-message hide checkboxes unchanged,
  along with the singular/plural label and stored-response behaviour.
- Show an empty Page cell when a message has no page number, instead of the
  placeholder text `None`.
- Show message text in a selectable, wrapping label instead of a focusable
  text view, so the read-only text cannot leave a text-input context behind
  when the dialog closes. This also removes the need for a post-map relayout
  of the message list.
- Return a response when the dialog is closed with Escape or the window close
  control, rather than only destroying the widget, so a caller waiting on the
  dialog does not hang.
- Add regression tests that assert the global control is outside the scrolled
  window, is mapped above the action area, that the message list fills the
  available height, that adjacent grid columns and rows have the configured
  gap, that message text is selectable, that an unknown page leaves an empty
  Page cell, and that Escape and the close control both return a response.

## Capabilities

### New Capabilities

<!-- None. -->

### Modified Capabilities

- `dialog-layout`: add requirements that a message dialog keeps its global
  hide control outside the scrolling message list and visible above the action
  buttons, that the message list fills the dialog's available height, that the
  message grid separates adjacent columns and rows, that an unknown page leaves
  an empty Page cell, and that the dialog returns a response when it is closed
  with Escape or the window close control.

## Impact

- `src/scantpaper/dialog/__init__.py`: restructure `MultipleMessage`'s content
  area, set the scrolled window to expand, set the message grid's column and
  row spacing, use a selectable label for message text, show an empty Page
  cell for an unknown page, and return a response on Escape and on the window
  close control.
- `src/scantpaper/tests/test_053_dialog_multiplemessage.py` and
  `src/scantpaper/tests/test_05_dialog.py`: add structural, spacing, layout,
  selectable-text, and close-response tests.
- `changelog.md`: record the user-visible dialog fix.
- No new dependencies and no data model changes.
- Out of scope: suppressing empty message rows and replacing the separate
  label plus checkbox with a single check button.
