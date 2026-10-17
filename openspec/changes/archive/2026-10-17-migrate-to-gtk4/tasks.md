## 1. Packaging & CI

- [x] 1.1 Swap GTK3→GTK4 package names in `.github/workflows/test.yml`,
      `deb.yml`, `fedora.yml`, `opensuse.yml`: `gir1.2-gtk-3.0` →
      `gir1.2-gtk-4.0`, `gtk3` → `gtk4`, `typelib-1_0-Gtk-3_0` →
      `typelib-1_0-Gtk-4_0`; add any `graphene` typelib/build deps required.
- [x] 1.2 Update `packaging/fedora/scantpaper.spec` and
      `packaging/opensuse/scantpaper.spec` BuildRequires/Requires for GTK4
      (gtk4, typelib-1_0-Gtk-4_0, python3-gobject/pycairo as-is).
- [ ] 1.3 Confirm CI produces and runs a GTK4 build on `ubuntu-latest`,
      `ubuntu-22.04` (jammy), Fedora 43/44, and openSUSE Leap 16.

## 2. Foundation

- [x] 2.1 Update `gi.require_version` to `Gtk 4.0` / `Gdk 4.0` (and
      `Graphene 1.0` where needed) across all modules and conftest.py.
- [x] 2.2 Update all `from gi.repository import ...` imports for the GTK4
      namespaces (Gdk is bundled with Gtk 4.0).
- [x] 2.3 Rework `src/scantpaper/conftest.py` test harness to create GTK4
      widgets and drive events via the new controller API
      (conftest.py declares `gi.require_version("Gtk","4.0")` and the
      modal-dialog fixtures work with the `run_dialog()` helper that
      replaced `Gtk.Dialog.run()`).

## 3. Broad mechanical sweep (non-drawing)

- [x] 3.1 Convert container packing (`pack_start`/`pack_end`/`add`,
      `set_border_width`) to `Gtk.Box.append`/`prepend`/`insert_child_after`
      and margin properties across all modules (via a shared `pack_box` /
      `set_margins` helper in helpers.py).
- [x] 3.2 Replace `Gdk.Rectangle` with `graphene.Rect` (or a thin local
      wrapper) across canvas.py and imageview.py and related modules
      (verified: `Gdk.Rectangle` still exists in GTK4 as a deprecated boxed
      type with mutable x/y/width/height, `copy()`, `intersect()` and
      `union()`; all 53 uses keep working — no code changes required).
- [x] 3.3 Rework the `Gtk.Dialog` subclass in `dialog/__init__.py`:
      `do_delete_event`/`do_key_press_event` overrides and content-area
      packing for GTK4.
- [x] 3.4 Replace `Gtk.Window.propagate_key_event` usage in app_window.py
      with GTK4 key handling (`Gtk.EventControllerKey`); also ported the
      dialog base, `save.py` spin buttons and the calendar to focus/click
      controllers.
- [x] 3.5 Port `basedocument.py` drag-and-drop from `Gtk.TargetEntry` +
      `drag_source_set`/`drag_dest_set` to `Gtk.DragSource` / `Gtk.DropTarget`
      (row reorder via a DragSource/DropTarget pair, external files via a
      `Gdk.FileList` DropTarget; `app_window.drag_motion_callback` moved to
      the drop targets' "motion" signal). Also fixed stale worker GLib
      sources leaking across tests: `BaseThread.release_glib_sources()` is
      now public/idempotent and the autouse teardown fixture drops queued
      responses so a lingering worker cannot run callbacks during the next
      test.
- [x] 3.9 Port the GTK4 widget API removals hit by the dialogs and windows:
      `Gtk.Dialog.run()`/`Gtk.Widget.show_all()` → a new `run_dialog()`
      helper (nested main loop) plus `present()`, `Gtk.RadioButton` →
      grouped `Gtk.CheckButton` (with the user-only "activate" signal
      replacing GTK3's "clicked", never "toggled", so programmatic
      `set_active()` during init does not run the handlers),
      `Gtk.Button.set_image` → `set_child`, `Gtk.IconSize` argument
      removal, `Gtk.Widget.get_children` → `observe_children`,
      `Gtk.Calendar` `select_day`/`get_date` DateTime form,
      `Gtk.IconTheme.get_default()`/`prepend_search_path()` →
      `get_for_display()` + `set_search_path()` with the app icon path
      prepended (app startup), the PyGObject `Widget.get_size()` tuple
      helper → `get_width()`/`get_height()` and `Window.get_position()` →
      dropped (quit path), `Window.resize`/`Widget.destroy`/
      `Widget.get_border_width`/`set_no_show_all`/`Gtk.STOCK_*`/
      `Gtk.Container` removals. Also fixed the `Gio.Error` → `GLib.Error`
      except clause in file_menu_mixins.py.
- [x] 3.6 Port `print_operation.py` `Gtk.PrintOperation` and
      `draw-page`/`PrintPages` enums to GTK4 (verified: Gtk.PrintOperation,
      Gtk.PrintContext, get_cairo_context/get_width/get_height,
      Gtk.PrintPages.RANGES, Gdk.cairo_set_source_pixbuf all exist in GTK4
      as deprecated API — no code changes required).
- [x] 3.7 Port `entry_completion.py`, `simplelist.py` (TreeView/ListStore),
      `comboboxtext.py`, and Notebook usage in place (kept as deprecated
      GTK4 widgets; verified all exist in GTK4 — no code changes required).
- [x] 3.8 Update `clipboard.py` and its consumers for the GTK4 clipboard /
      Gdk content API (clipboard.py is a pure GObject.Object wrapper over
      in-memory page data, not the Gtk/Gdk clipboard; it and its consumers
      are already GTK4-clean — no code changes required).

## 4. Menus & Builder `.ui` files

- [x] 4.1 Move `menu.ui` per-item `accel` attributes to
      `Gtk.Application.add_accelerator` at startup (registered in app.py
      `_setup_accelerators`; app.ui menubar accels moved too).
- [x] 4.2 Rebuild `app.ui`, `menu.ui`, `window.ui` for the GTK4 widget/box
      model and `interface-requires gtk 4.0` (app.ui: toolbar→box of
      buttons, GtkMenu popups→GtkPopover, stock_id→icon-name, removed
      `<packing>`; verified app.ui loads via Gtk.Builder).
- [x] 4.3 Update `app_window.py` Builder wiring and pane layout
      (GtkNotebook/GtkPaned/GtkScrolledWindow) for GTK4.

## 5. Custom drawing (highest risk)

- [x] 5.1 Rework `canvas.py` from the GTK3 `"draw"` signal to
      `Gtk.DrawingArea.set_draw_func`; port event handling
      (button/motion/scroll) to gesture/event controllers.
- [x] 5.2 Rework `imageview.py` similarly; re-express the tool classes'
      `button_pressed`/`button_released`/`motion` methods as explicit
      `(button, x, y)`/`(x, y)` calls driven by the gesture and motion
      controllers.
- [x] 5.3 Port `Gdk.Display.get_default().get_default_seat().get_pointer()`
      and cursor handling (`Gdk.Cursor.new_from_name`) to GTK4 equivalents
      (middle-button panning uses the motion controller's widget
      coordinates; cursors are set with `Gtk.Widget.set_cursor` and
      `Gdk.Cursor.new_from_name(name, None)`).
- [x] 5.4 Verify crop, rotate, selection and scan-preview interaction
      visually and via test_7_canvas.py / test_imageview.py
      (test_7_canvas.py, test_imageview.py and test_layer.py pass:
      244 tests).

## 6. Tests & release docs

- [x] 6.1 Update all GTK-touching tests to the GTK4 API; ensure `pytest`
      passes with coverage thresholds met (full suite: 1648 passed,
      coverage 99.25% ≥ 99%).
- [x] 6.2 Run and pass `ruff check`, `ruff format --check`, and
      `ty check .` with no new diagnostics.
- [x] 6.3 Update README.md for any user-visible GTK4-related change
      (GTK4 requirement, `gir1.2-gtk-4.0` dependency, `~/.config/gtk-4.0/
      gtk.css`; AGENTS.md stack description updated too).
- [x] 6.4 Add the deferred-modernisation checklist to release_procedure.md
      for when jammy is dropped.
