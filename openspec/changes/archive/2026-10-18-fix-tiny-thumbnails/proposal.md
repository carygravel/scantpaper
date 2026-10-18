# Fix tiny thumbnails

## Why

Since the GTK3 to GTK4 migration, page thumbnails in the thumbnail panel are
painted at roughly 24x15 px instead of their generated size of up to 100 px,
which makes them useless for telling pages apart. The generated pixbufs and
the widget layout are correct; only the on-screen paint is wrong, so existing
model-level tests cannot catch it.

Root cause (verified against GTK 4.24.1 source and by live measurement):
`GtkCellRendererPixbuf` in GTK4 draws through a `GtkIconHelper`, which clamps
the painted size to the CSS property `-gtk-icon-size` (16 px on the `.image`
style class that the renderer adds to the TreeView's CSS node), regardless of
the pixbuf's intrinsic size. GTK3 painted the pixbuf at its own pixel size.

## What Changes

- Scope a GTK CSS rule to the document thumbnail list,
  `treeview.image { -gtk-icon-size: <THUMBNAIL>px; }`, so the renderer paints
  thumbnails at their generated size. The pixel value is derived from the
  `THUMBNAIL` constant, not duplicated as a literal.
- Register the application's first `Gtk.CssProvider` at startup for this rule.
- Add a paint-level regression test that snapshots the thumbnail list widget
  and asserts the thumbnail is painted at its generated size (CI already runs
  the suite under `pytest-xvfb`).

## Capabilities

### New Capabilities
- `thumbnail-display`: Governs how thumbnails are painted in the thumbnail
  panel: each page's thumbnail SHALL be painted at the size it was generated
  at, not scaled down to a stylesheet icon size.

### Modified Capabilities

## Impact

- `src/scantpaper/app_window.py`: attach the CSS provider; add a scoping CSS
  class to the document list widget.
- `src/scantpaper/const.py`: `THUMBNAIL` stays the single source of truth for
  the icon-size value.
- `src/scantpaper/tests/`: new paint-level regression test.
- No model, storage, or thumbnail-generation changes; no new dependencies.
