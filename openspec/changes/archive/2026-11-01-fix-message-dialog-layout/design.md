# Design

## Context

See `proposal.md` for motivation and `specs/dialog-layout/spec.md` for the
behaviour contract.

`MultipleMessage` currently builds one `Gtk.Grid` containing the header row,
one row per message, and the global hide label and checkbox. The grid is the
child of a `Gtk.ScrolledWindow`, which is the only child of the dialog's
content area.

Measurements with one empty message and `store-response=True`:

- dialog: `600 x 200`
- content area: `576 x 46`
- scrolled window: `576 x 46`
- grid: `561 x 57`
- global checkbox row: `y=38..57`, clipped by the 46 px viewport
- action area: `y=70..128`, leaving 72 px unused below it

`Gtk.ScrolledWindow` does not propagate its child's natural height by default,
so it reports a natural height of 46 px even though the grid needs 57 px.
Setting `vexpand=True` on the scrolled window makes the content area expand to
118 px at the same dialog size and moves the action area to the bottom.
Setting it alone would still leave the global checkbox inside the scrolling
list, where many messages could scroll it out of view.

## Goals / Non-Goals

**Goals:**

- Keep the global hide control fully visible above the action buttons.
- Let the message list use the dialog's available height.
- Separate the message grid's columns and rows with the dialog's standard
  spacing.
- Preserve the existing message-row layout, per-message hide checkboxes,
  singular/plural label, and stored-response behaviour.
- Add regression tests for the structure, spacing, and visible layout.

**Non-Goals:**

- Suppressing empty message rows.
- Replacing the separate label and checkbox with a single check button.
- Hiding the global control when no message supports storing a response.
- Changing how messages are filtered, split, or stored.

## Decisions

### Move the global control into a fixed row below the scrolled window

The label and checkbox will move from the grid into a `Gtk.Box` appended to the
content area after the scrolled window. The box keeps the existing
label-on-the-left, checkbox-on-the-right arrangement: the label expands and
aligns to the end, and the checkbox stays at the right edge.

Keeping the control in the grid and only setting `vexpand=True` was rejected:
it fixes the clipping but lets the control scroll away when there are many
messages. A fixed row is the only arrangement that keeps it available in both
the one-message and many-message cases.

### Make the scrolled window expand

The scrolled window will set `vexpand=True`. It will remain the first child of
the content area, with the global control box directly below it. The action
area stays a sibling of the content area and therefore remains below both.

Setting a fixed minimum height was rejected because it would not adapt to the
dialog size and could reintroduce clipping in a short dialog. Setting
`propagate_natural_height=True` was rejected because it only grows the list to
its content height; it does not use surplus dialog height.

### Use the dialog spacing constant for both grid axes

`Gtk.Grid` defaults both `column-spacing` and `row-spacing` to zero, so the
header cells, message cells, and hide checkboxes currently touch. The grid
will set both to `DIALOG_ROW_SPACING` (`6`), the same value used between blocks
in the dialog content area.

A hard-coded `6` was rejected because it duplicates a layout constant that
already exists. Per-cell margins were rejected because they would have to be
applied to every header and message widget and would not keep the columns
aligned.

The column spacing adds four gaps to the five-column grid, so its natural width
grows by about `4 * 6 = 24` px. The row spacing adds `6` px between each pair of
message rows. Both are acceptable: the scrolled window already handles
overflow, and the dialog's default width leaves room for the extra width.

### Keep the grid and its row accounting unchanged

The grid will contain only the header row and the message rows. `grid_rows`
will continue to mean one header plus the number of message rows, so
`show_message_dialog()` still runs only when there is at least one message.
`_list_checkbuttons()` and `list_messages_to_ignore()` keep scanning the
message rows for per-message checkboxes.

The global control is no longer a grid cell, so it cannot be found by those
scans. That is intentional: it is the aggregate control, not a per-message
response.

### Show an empty Page cell for an unknown page

A message's `page` value may be `None` when the message is not tied to a
document page.  The Page column is a plain label, so rendering `str(page)`
would show the literal text `None` to the user.  The cell will use an empty
label instead; messages with a page number keep their current representation.

### Use a selectable label for message text

Each message cell will be a `Gtk.Label` with wrapping and `selectable=True`
instead of a `Gtk.TextView`. A focused text view creates a GTK input-method
context. With `ibus-gtk4` 1.5.35~rc1 on GTK 4.24.1, closing the dialog while
the text is focused makes the IBus module call
`gdk_x11_surface_get_xid(NULL)` on focus-out and segfault. A selectable label
keeps mouse selection and copying, does not create an input-method context,
and does not report the pathological narrow-width height that a wrapping text
view does, so the post-map relayout of the message list is no longer needed.
Stored responses are read with `get_text()` rather than from a text buffer.

Escape and the window close control will return a close response and hide the
dialog. The previous behaviour destroyed the widget from inside its own event
handler and left a caller waiting in `run_dialog()` with nothing to wake it.

### Keep the separate label and checkbox

The existing label plus checkbox will be preserved rather than replaced by
`Gtk.CheckButton.new_with_label()`. This keeps the current right-aligned
label and right-edge checkbox, and avoids changing the click target or the
visual arrangement in the same fix. A single check button remains a possible
accessibility improvement, but it is outside this change.

### Verify with structure first and allocation second

The tests will assert the durable structure: the global label and checkbox are
not descendants of the scrolled window, their parent is the fixed row, and the
scrolled window requests vertical expansion. They will also assert that the
grid's column and row spacing equal `DIALOG_ROW_SPACING`. They will then present
the dialog at a known size and assert that the global checkbox is mapped and
ends above the action area, that the scrolled window is taller than its natural
row height, and that adjacent header cells have a visible gap.

Allocation assertions will use the project's existing wait-until pattern so
they run after GTK has allocated the widgets. Structural assertions remain the
primary regression guard if a platform reports slightly different sizes.

## Risks / Trade-offs

- **Allocation tests can be timing- or theme-sensitive.** Mitigation: wait for
  the dialog and checkbox to be mapped, assert ordering rather than exact
  pixel heights where possible, and keep structural assertions that do not
  depend on the theme.
- **The global control is still shown when no message supports storing a
  response.** This is pre-existing behaviour and is left unchanged. Mitigation:
  keep it out of this change; it can be a separate refinement.
- **A very narrow dialog may squeeze the global label.** Mitigation: the label
  expands and the checkbox keeps its natural width; wrapping can be considered
  separately if a real dialog shows truncation.
- **The scrolled window now consumes surplus height that previously appeared
  below the action area.** This is the intended behaviour for a scrolling
  message list, and the rows themselves keep their natural height.
- **Grid spacing increases the message list's natural width and height.** The
  width grows by about 24 px and each row gap adds 6 px, so a very narrow
  dialog or a long message list scrolls sooner. Mitigation: the list already
  scrolls in both directions, and the default dialog width leaves room for the
  extra column gaps.

## Migration Plan

No data or configuration migration is required. The change is local to the
message dialog's widget tree and its tests. Reverting it restores the previous
layout without affecting stored messages or responses.
