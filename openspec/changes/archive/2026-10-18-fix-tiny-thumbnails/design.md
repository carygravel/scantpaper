# Design: fix tiny thumbnails

## Context

The GTK4 migration commit (e4e067a2) changed how `Gtk.CellRendererPixbuf`
paints: GTK4 routes the pixbuf through a `GtkIconHelper` exposed as a
`GdkPaintable`. In `gtk_icon_helper_paintable_snapshot()` (GTK 4.24.1) the
drawn size is clamped:

```c
h = MIN (height, gtk_icon_helper_get_size (self));
w = h * ratio;
```

`gtk_icon_helper_get_size()` returns `pixel_size` if set (the renderer never
sets it) and otherwise the CSS property `-gtk-icon-size`, which resolves to
16 px for the `.image` style class the renderer adds to the TreeView's CSS
node. Cell allocation still uses the pixbuf's intrinsic size, so the column
and row are laid out correctly (cell area 100x65, column width 104) while the
paint is 24x15. This is why the model-level tests pass.

Verified by live measurement under Xvfb with the real `ApplicationWindow`:
without a CSS override the thumbnail paints 24x15; with
`treeview.image { -gtk-icon-size: 100px; }` it paints 100x65 (clipped by the
100 px panel, as expected).

Constraints:

- Thumbnails are generated at `THUMBNAIL = 100` px
  (`src/scantpaper/const.py:87`); generation is correct and out of scope.
- The application currently installs no `Gtk.CssProvider` anywhere.
- The only `pixbuf`-typed `SimpleList` column is the document thumbnail list
  (`BaseDocument.__init__`); no other widget is affected by the scoping
  decision below.

## Goals / Non-Goals

**Goals:**

- Thumbnails paint at their generated size, satisfying the
  `thumbnail-display` spec.
- The paint value is derived from `THUMBNAIL`, keeping one source of truth.
- A regression test that fails before the fix and passes after (paint-level,
  not model-level).

**Non-Goals:**

- Migrating the thumbnail list off `Gtk.TreeView`/`SimpleList` to
  `Gtk.GridView` + `Gtk.Picture` (modernization; separate change).
- Rendering thumbnails at device scale for HiDPI sharpness (same 100 CSS px
  as GTK3; can be revisited separately).
- Fixing other GTK4 migration rendering bugs.

## Decisions

### Decision: CSS override instead of a custom cell renderer

Use a scoped GTK CSS rule,
`-gtk-icon-size: <THUMBNAIL>px` on the document list, rather than
subclassing `Gtk.CellRendererPixbuf` to draw the texture directly.

Rationale: the CSS rule is ~5 lines, was verified to fix the paint, and keeps
the renderer's own padding, alignment and selection-drawing behaviour
untouched. A custom `do_snapshot` override would have to reimplement cell-area
arithmetic (padding, x/y alignment, expander handling) to avoid visual
regressions, for no functional gain.

Alternatives considered and rejected:

- Setting the renderer's `icon-size` property to `Gtk.IconSize.LARGE`:
  clamps to 32 px, still wrong; only `INHERIT` avoids the lookup, and the
  helper then falls back to the CSS value.
- Using the `texture` property instead of `pixbuf`: the same helper clamps
  paintable definitions either way.
- GridView migration: right long-term fix for deprecated TreeView, but far
  too large for a bugfix (drag-and-drop reordering, inline page-number
  editing, multi-select all move with it).

### Decision: scope the rule by a dedicated CSS class on the document list

`SimpleList` is a plain `Gtk.TreeView`; the renderer adds the `image` class to
the treeview node itself at paint time. Scope the rule with a CSS class (e.g.
`thumbnail-list`) added to the `BaseDocument` widget in its `__init__`, and
match `.thumbnail-list.image`, rather than a bare `treeview.image` global
rule. This keeps the override local to the thumbnail list even if another
`SimpleList` pixbuf column appears later. The provider is registered at
application startup with `STYLE_PROVIDER_PRIORITY_APPLICATION`.

### Decision: paint-level regression test via Gtk.Snapshot

The test imports a page into a real `Document`, realizes the widget, snapshots
the thumbnail list with `Gtk.Snapshot` via `snapshot_child`, converts the
paintable to a PNG, and asserts the painted thumbnail region is the generated
pixbuf size (within clipping tolerance for the panel edge). CI already runs
pytest under `pytest-xvfb`, so a mapped widget is available. A model-only
assertion is not sufficient here (that is what the existing tests do, and it
does not regress).

## Risks / Trade-offs

- [Reliance on undocumented renderer internals (`-gtk-icon-size` and the
  `image` class)] → The clamp behaviour is stable across GTK4.x because
  `CellRendererPixbuf`'s GTK4 implementation is built on the icon helper; the
  paint-level test fails loudly if GTK changes it, and the fix reduces to
  updating the CSS rule.
- [`-gtk-icon-size` on the treeview node also affects any other pixbuf
  renderer in that treeview] → The document list is the only pixbuf column
  today, and the rule is scoped by class rather than global.
- [A static CSS px value could drift from `THUMBNAIL`] → The rule is built
  from `THUMBNAIL` with an f-string, so the constant stays the single source
  of truth; no second literal is introduced.

## Migration Plan

Single commit bugfix; no data, config, or packaging changes. Rollback is
reverting the commit.

## Open Questions

None.
