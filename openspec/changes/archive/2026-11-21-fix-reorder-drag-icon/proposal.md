# Proposal

## Why

Dragging a page in the thumbnail panel to reorder it shows the literal text
`scantpaper-rows` beside the pointer. GTK 4 creates a default drag icon from
the drag source's content provider, and the provider currently carries that
internal sentinel as a plain string, so GTK renders it as a label. The text is
not page content and makes a routine action look broken. This is a regression
from the GTK 3 port: the old target-entry API did not synthesize a label from
the payload.

## What Changes

- Set a custom drag icon on the thumbnail list's `Gtk.DragSource` when a
  reorder drag begins.
- Use the first selected page's thumbnail as the icon, so the icon represents
  what is being moved.
- Use a transparent 1x1 fallback when no thumbnail is available, so the
  payload text can never appear.
- Leave the string payload, drop target types, and reorder semantics unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `page-reordering`: add a requirement that the reorder drag icon represents
  the dragged page and never displays the internal payload.

## Impact

- `src/scantpaper/basedocument.py`: connect `drag-begin` and set the icon from
  the selected row's thumbnail.
- `src/scantpaper/tests/test_basedocument.py`: unit tests for the thumbnail,
  no-selection, missing-thumbnail, and multi-selection cases.
- `README.md` and `changelog.md`: describe the visible fix.
- No new dependencies. `Gdk.Texture.new_for_pixbuf` is available at the
  supported GTK 4.6 floor.
