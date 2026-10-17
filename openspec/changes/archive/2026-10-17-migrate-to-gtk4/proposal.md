## Why

GTK3 is end-of-life upstream: it receives no new development or security
fixes and is increasingly a poor fit for modern Wayland/HiDPI environments.
The project is fully pinned to `gi.require_version("Gtk", "3.0")` (plus
Gdk 3.0, GdkPixbuf 2.0) across ~20 modules and three Gtk.Builder `.ui`
files. GTK4 has been stable since 2020 and is shipped by every distro in the
CI matrix (jammy 4.6.9 through Fedora 44 4.22.5), so the platform is ready.

This is a faithful **port**, not a redesign: user-visible behaviour stays
identical. GTK4 will be targeted with the APIs available on the oldest CI
distro (Ubuntu 22.04 jammy, GTK 4.6.9), so the `oldest` job keeps passing.
Modernising onto newer GTK4 widgets is deliberately deferred until jammy is
dropped (see the release_procedure.md checklist).

## What Changes

- Change every `gi.require_version("Gtk", "3.0")` (and `Gdk 3.0`) to GTK4
  (`Gtk 4.0`); update imports across all modules.
- Rework the two custom-drawn widgets — `Canvas` (canvas.py) and `ImageView`
  (imageview.py) — from the GTK3 `Gtk.DrawingArea` + `"draw"` signal and
  event signals (`button-press-event`, `motion-notify-event`,
  `scroll-event`) to GTK4's `set_draw_func()` and `Gtk.GestureClick` /
  `Gtk.EventControllerMotion` / `Gtk.EventControllerScroll` /
  `Gtk.EventControllerKey`.
- Replace GTK3-only event data types (`Gdk.EventButton`, `Gdk.EventMotion`,
  `Gdk.EventKey`, `Gdk.EventMask`, `Gdk.EVENT_*`/`Gdk.KEY_*`) and
  `Gdk.Rectangle` (→ `graphene.Rect`) throughout.
- Convert the GTK3 container packing API (`pack_start`/`pack_end`/`add`,
  `set_border_width`) to GTK4's `Gtk.Box.append`/`prepend`/`insert_child_after`
  and margin properties.
- Rebuild the three Gtk.Builder `.ui` files (app.ui, menu.ui, window.ui) for
  the GTK4 widget/box model and `interface-requires gtk 4.0`.
- Rewire the menu model (menu.ui) for GTK4: the GAction-based `<menu>` tree
  survives, but per-item `accel` attributes move to
  `Gtk.Application.add_accelerator`.
- Replace GTK3 drag-and-drop on `basedocument.py` (`Gtk.TargetEntry`,
  `drag_source_set`/`drag_dest_set`) with the GTK4 `Gtk.DragSource` /
  `Gtk.DropTarget` API.
- Rework the `Gtk.Dialog` subclass boilerplate (dialog/__init__.py) and the
  `Gtk.Window.propagate_key_event` calls in app_window.py for GTK4.
- Update the packaging (workflows, deb/fedora/opensuse specs) from GTK3 to
  GTK4 package names (`gir1.2-gtk-4.0`, `gtk4`, `typelib-1_0-Gtk-4_0`).
- Update the test harness (conftest.py and affected tests) to the GTK4 API.
- Keep the already-deprecated GTK4 widgets the app uses today (TreeView /
  ListStore / ComboBox / Notebook / Dialog / EntryCompletion /
  PrintOperation). No modernisation in this change.
- **BREAKING**: raises the minimum toolkit from GTK3 to GTK4 (jammy stays
  supported; the supported Ubuntu floor becomes 22.04).

## Capabilities

### New Capabilities

None — this is a pure refactor with no user-visible behaviour change.

### Modified Capabilities

None — no spec-level requirement changes. `skip_specs: true` is set in
`.openspec.yaml` because behaviour is unchanged; the GTK3→GTK4 swap is an
internal implementation change only.

## Impact

- **Code**: every module that imports `Gtk`/`Gdk` (canvas.py, imageview.py,
  app_window.py, basedocument.py, all `dialog/*`, the `*_menu_mixins.py`,
  print_operation.py, simplelist.py, entry_completion.py, comboboxtext.py,
  layer.py, pagerange.py, session_mixins.py, progress.py, unpaper.py,
  helpers.py, conftest.py). ~25k lines of Python + ~1k lines of `.ui`.
- **Highest-risk area**: the custom drawing and event handling in canvas.py
  and imageview.py (GtkDrawingArea → set_draw_func + gesture controllers).
- **Dependencies**: `gir1.2-gtk-3.0` → `gir1.2-gtk-4.0` (Debian/Ubuntu),
  `gtk3` → `gtk4` + `typelib-1_0-Gtk-4_0` (Fedora/openSUSE), plus
  `graphene`/`graphene-1.0` typelibs. pygobject on every target already
  supports GTK4 bindings (jammy's 3.42.0 is sufficient).
- **Packaging**: `.github/workflows/*.yml` and `packaging/*` specs.
- **Tests**: conftest.py plus the GTK-touching tests in the suite.
