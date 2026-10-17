## Context

See proposal.md for the motivation. The current code is pinned to GTK3 in
every module: `gi.require_version("Gtk", "3.0")` (plus `Gdk 3.0`,
`GdkPixbuf 2.0`, `Pango`, `PangoCairo`), three Gtk.Builder `.ui` files
(app.ui, menu.ui, window.ui), and ~20 modules touching `Gtk`/`Gdk`.

Two files carry nearly all of the custom-rendering risk:

- `canvas.py` (1,834 lines) — subclasses `Gtk.DrawingArea`, draws a scene
  graph of OCR text + annotations with Cairo via the GTK3 `"draw"` signal,
  and handles button/motion/scroll events via GTK3 event signals. Uses
  `Gdk.Rectangle` throughout and
  `Gdk.Display.get_default().get_default_seat().get_pointer()`.
- `imageview.py` (988 lines) — also subclasses `Gtk.DrawingArea`, with a set
  of tool classes (`button_pressed`/`button_released`/`motion` methods) that
  each read `Gdk.EventButton`/`Gdk.EventMotion`.

The rest of the migration is broad but mechanical (container packing, event
data types, dialog overrides). The menu system is already GAction-based
(`menu.ui` references `app.*` actions) which is exactly GTK4's model.

Constraint that shapes the whole design: the port must run on the oldest CI
distro, Ubuntu 22.04 jammy (GTK 4.6.9, glib 2.72, pygobject 3.42.0), so the
`oldest` CI job keeps passing. GTK4 widgets introduced after 4.6 (e.g.
`GtkDropDown` 4.10, `GtkAlertDialog` 4.10) are therefore out of scope.

## Goals / Non-Goals

**Goals:**
- Faithful port to GTK4 with zero intentional user-visible behaviour change.
- Runs unchanged on GTK 4.6.9 (jammy), so the `oldest` CI job stays green.
- Keep the already-deprecated GTK4 widgets the app uses today; do not
  rewrite them.
- Tests (pytest) pass and the ruff/ty gates stay clean.

**Non-Goals:**
- Adopting GTK4 widgets newer than 4.6 (`GtkDropDown`, `GtkAlertDialog`,
  `GtkColumnView`, `GtkStringList`-based lists, `GtkBoxLayout` GLADE
  redesign). Deferred to a follow-up after jammy is dropped — tracked in
  release_procedure.md.
- Changing any user-visible behaviour, layout, or keyboard shortcuts.
- Supporting GTK3 in parallel (impossible — GTK3 and GTK4 cannot coexist in
  one process).

## Decisions

**D1. Port as a single coordinated branch, not incremental.** GTK3 and GTK4
cannot coexist in one process, so the codebase flips over in one change.
Mitigation: the change is split into tasks ordered bottom-up
(non-drawing first, canvas/imageview last) and each task lands only when
its tests pass. The ~80 tests are the safety net.

**D2. Custom drawing keeps the Cairo path via `set_draw_func`.** GTK4's
`GtkDrawingArea` still hands a Cairo context to a draw function, so the
existing `_draw_scene`/tool-drawing Cairo code ports with minimal churn —
we do not adopt the snapshot `GtkSnapshot`/`GtkGLArea` API. Rationale:
lowest-risk path to keep the substantial Cairo scene graph intact.

**D3. Replace GTK3 event signals with `Gtk.EventController`s.** Each
GTK3 event-signal handler becomes one of `Gtk.GestureClick` (press/release),
`Gtk.EventControllerMotion` (motion), `Gtk.EventControllerScroll` (scroll),
`Gtk.EventControllerKey` (keyboard). The tool classes in imageview.py
(`button_pressed`/`button_released`/`motion`) are re-expressed as gesture /
motion controllers. Rationale: GTK4 removed the event signals entirely.

**D4. Use `graphene.Rect` in place of `Gdk.Rectangle`.** `Gdk.Rectangle`
(53 uses) is gone in GTK4. Introduce a thin local wrapper or migrate call
sites to `graphene.Rect` (via `gi.require_version("Graphene", "1.0")`) —
decided by whichever keeps the diff smallest, since `graphene.Rect` lacks a
few convenience methods used in canvas.py.

**D5. Keep the GAction `<menu>` model; move accelerators.** `menu.ui`'s
GAction-based `<menu>` structure survives in GTK4. The GTK3 per-item
`accel` attribute does not: move every shortcut to
`Gtk.Application.add_accelerator` at startup (keys as `"<Primary>n"` etc.),
matching the labels' mnemonics. Rationale: least-change path that preserves
the existing menus.

**D6. Port the dialogs' `Gtk.Dialog` subclass without adopting
`Gtk.AlertDialog`.** `Gtk.Dialog` still exists in GTK 4.6 (deprecated), so
dialog/__init__.py ports mechanically: `do_delete_event`/`do_key_press_event`
overrides become `Gtk.EventControllerKey`/close handling, and
`get_content_area().pack_start(...)` becomes `get_content_area().append(...)`.
Rationale: jammy's GTK 4.6.9 predates `Gtk.AlertDialog` (4.10); modernising
is deferred.

**D7. Port drag-and-drop to `Gtk.DragSource` / `Gtk.DropTarget`.**
`basedocument.py`'s `Gtk.TargetEntry` + `drag_source_set`/`drag_dest_set`
(used for page reordering in the tree) maps to GTK4's `Gtk.DragSource` and
`Gtk.DropTarget` with content providers. The `Gdk.Atom`-based target list
logic in basedocument.py needs rework to GTK4 content models.

**D8. PrintOperation keeps its Cairo draw path.** `Gtk.PrintOperation`
exists in GTK 4.6 and `draw-page` still provides a Cairo context
(`PrintContext.get_cairo_context()`), so print_operation.py ports with only
type/enum changes (`Gtk.PrintPages.RANGES` etc.).

## Risks / Trade-offs

- [Canvas/imageview drawing + event rework is the highest-risk, hardest to
  get right] → Mitigation: isolate into dedicated tasks, port tool classes
  one at a time, lean on the existing test_7_canvas.py / test_imageview.py
  tests; keep the Cairo rendering engine unchanged so only the wiring (draw
  func + controllers) is new.
- [Subtle event-handling differences (grab semantics, button ordering)
  could change crop/selection UX] → Mitigation: add/adjust tests that
  simulate pointer events via the new controllers; visually verify crop,
  rotation and selection in the three scan modes during release testing
  (release_procedure.md step 1).
- [The `.ui` files need a GTK4 rewrite and Builder API differences can be
  finicky] → Mitigation: treat app.ui/window.ui as a contained task; keep
  the widget hierarchy equivalent; validate each dialog loads via Builder
  in tests.
- [GTK 4.6 deprecation warnings could tempt mid-port modernisation and
  break the floor] → Mitigation: explicitly ban 4.10+ APIs in review; the
  modernisation list lives in release_procedure.md for after jammy is
  dropped.
- [Keybinding behaviour could drift when moving from `accel` attributes to
  `add_accelerator`] → Mitigation: keep the exact same `"<Primary>..."`
  strings; verify with the existing shortcut tests.

## Migration Plan

Single coordinated change, applied via `/opsx-apply`. Task order
(bottom-up):

1. Packaging: swap GTK3→GTK4 package names in workflows and specs so a
   GTK4 build can be produced and CI can exercise it.
2. Foundation: update `gi.require_version` calls, imports, `Graphene`
   availability, and conftest.py harness to GTK4.
3. Broad mechanical sweep: container packing (`pack_start`/`pack_end`/`add`,
   `set_border_width`), `Gdk.Rectangle`→`graphene.Rect`, dialog subclass,
   `propagate_key_event`, clipboard/DnD, PrintOperation, EntryCompletion,
   TreeView/ListStore/ComboBox, Notebook usage.
4. Menus: rewire accelerators; rework the three `.ui` files.
5. Custom drawing: canvas.py then imageview.py (`set_draw_func` + gesture
   controllers + tool-class rework).
6. Full `pytest`, `ruff`, `ty` gate; update release_procedure.md.

Rollback: the change is coordinated and git-backed; a failing state is
reverted wholesale rather than hot-patched, since GTK3/GTK4 can't coexist.

## Open Questions

- Whether to introduce a thin `graphene.Rect`-compatible wrapper in canvas.py
  or refactor call sites directly (D4) — an implementation detail that does
  not change the approach or task breakdown; pick whichever minimises diff.
- Whether `Gtk.EntryCompletion`'s GTK4 API changes are small enough to
  port in place or warrant the deferred `Gtk.DropDown` migration — confirmed
  small enough by the code size (92 lines), so handled in the sweep; the
  DropDown replacement stays deferred.
