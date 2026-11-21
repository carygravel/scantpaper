# Design

## Context

See `proposal.md` for the motivation. The relevant current state:

- `BaseDocument.__init__` creates a `Gtk.DragSource` with a `prepare` handler
  that returns `Gdk.ContentProvider.new_for_value("scantpaper-rows")`
  (`src/scantpaper/basedocument.py`).
- No icon is set on the source. GTK 4's
  `gtk_drag_source_ensure_icon()` therefore calls
  `gtk_drag_icon_create_widget_for_value()`, which turns a `G_TYPE_STRING`
  value into a `Gtk.Label` showing the string. That is the visible text.
- The string is only an internal sentinel: `_on_rows_accept` uses the
  `_internal_drag` flag, and `_on_drop_rows` ignores the value.
- The project supports GTK 4.6 / PyGObject 3.42 as its floor. The thumbnail
  column already holds a `GdkPixbuf.Pixbuf` for each page.

## Goals / Non-Goals

**Goals:**

- Remove the internal payload text from the drag icon.
- Show a useful icon that represents the page being moved.
- Guarantee the text cannot reappear when a thumbnail is missing.
- Keep the existing payload, drop target, and reorder behaviour unchanged.

**Non-Goals:**

- Changing the DnD payload type or preventing the internal sentinel from being
  offered to external applications as text.
- A multi-page badge or composite icon.
- Scaling or restyling the thumbnail beyond the existing 100 px size.
- A custom drop-position indicator (still deferred from the crash fix).

## Decisions

### Set the icon in a `drag-begin` handler

Connect `drag-begin` on the existing `Gtk.DragSource` and call
`Gtk.DragSource.set_icon()` there.

Rationale: `drag-begin` is the documented hook for drag icons, keeps the
`prepare` handler focused on returning the content provider, and leaves the
existing `prepare` tests unchanged. `set_icon()` is also allowed in `prepare`,
but that would mix icon selection with content selection and would need the
x/y coordinates passed to `prepare`.

### Use the first selected page's thumbnail

Read `self.data[rows[0]][1]` for the topmost selected row and convert it with
`Gdk.Texture.new_for_pixbuf()`.

Rationale: the reorder moves the whole selection, so one selected page is a
stable representative. The pixbuf is already loaded, so no image I/O is
needed. Showing the row under the pointer would be slightly more precise, but
would require storing the grabbed row or setting the icon in `prepare`; the
extra state is not justified.

Alternatives considered:

- **Row under the pointer:** more precise for a multi-selection, but adds
  state to clear at drag end. Deferred.
- **Composite icon with a count badge:** better feedback for large selections,
  but more code and a new visual design. Out of scope.

### Use a transparent 1x1 texture as the fallback

When there is no selected row, or the selected row has no pixbuf, set a 1x1
transparent `Gdk.MemoryTexture` as the icon.

Rationale: it guarantees the payload label can never appear, adds no visual
noise, and needs no themed-icon lookup. The fallback is a single expression.

Alternatives considered:

- **Leave GTK's default:** the text returns for a page whose thumbnail is not
  ready, which violates the requirement.
- **Generic document icon:** always gives feedback, but needs an icon theme
  lookup and a themed icon that may be missing.
- **Change the payload to a non-string type:** GTK would show its generic
  `text-x-generic` icon instead of text, but that changes the drop target type
  and the DnD contract for a cosmetic fix.

### Keep the string payload and drop target

The payload remains `"scantpaper-rows"` and the row drop target remains
`GObject.TYPE_STRING`.

Rationale: the value is internal and the icon is now independent of it.
Changing the type would ripple into `_on_drop_rows`, the accept logic and the
tests without improving the visible result.

### Hotspot at the icon's top-left

Call `set_icon(texture, 0, 0)`.

Rationale: the thumbnail hangs down and to the right of the pointer, so it
does not cover the row above the pointer. The existing 100 px thumbnail is
used as-is; if field feedback shows it obscures too much of the list, the size
or hotspot can be tuned without changing the spec.

## Risks / Trade-offs

- **A thumbnail is missing, is not a pixbuf, or no row is selected at drag
  begin** -> use the transparent fallback so the payload label cannot appear.
- **A 100 px icon obscures rows below the pointer** -> accepted for now;
  hotspot and size are easy to tune later.
- **The icon texture is held by the source between drags** -> the next drag
  replaces it with a new texture; at most one texture is retained.
- **The icon path touches DnD code covered by the crash fix** -> setting an
  icon does not arm the TreeView drop highlight; rerun the existing
  display-backed crash-gate tests.
- **Wayland and X11 render drag icons differently** -> both use the same
  `Gtk.DragSource.set_icon` path; no platform branch is added.
