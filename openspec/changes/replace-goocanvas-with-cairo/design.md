## Context

The current Canvas widget subclasses `GooCanvas.Canvas` and builds a GooCanvas scene graph where each OCR word becomes three GObjects: a `CanvasGroup` (Bbox), a `CanvasRect`, and a `CanvasText`. This per-word GObject overhead causes poor performance on dense pages (~1500 words) and blocks GTK4 migration since GooCanvas has no GTK4 port.

The codebase already has a working pattern for custom drawing: `ImageView` subclasses `Gtk.DrawingArea` and renders images via Cairo with zoom, pan, offset, tools, selection, and scroll support. The Canvas replacement follows the same architecture.

External constraints:
- Stay on GTK3 for now — GTK4 migration is a separate change
- Keep `app_window.py` integration unchanged (bind_property on zoom/offset, signal interface)
- Remove the `gir1.2-goocanvas-2.0` dependency from CI, packaging, and README
- No new Python dependencies (PyCairo and PyGObject already present)

## Goals / Non-Goals

**Goals:**
- Replace GooCanvas with a `Gtk.DrawingArea` + Cairo implementation that renders faster
- Preserve all external APIs: `Canvas` class with `zoom`, `offset`, `set_text()`, `clear_text()`, `sort_by_confidence()`, `sort_by_position()`, signal emissions
- Preserve the internal Bbox tree for scene graph traversal, editing, and hOCR export
- Keep confidence coloring, text rotation, and bounding box display
- Remove all GooCanvas imports and dependencies

**Non-Goals:**
- GTK4 migration — this change stays on GTK3 with `gi.require_version("Gtk", "3.0")`
- Changing the annotation canvas behavior (separate Canvas instance, same interface)
- Changing the iteration/index logic (TreeIter, ListIter) — these operate on the Bbox data model and don't need rewriting
- Performance beyond eliminating GooCanvas overhead (no spatial indexing yet — linear scan is sufficient for typical OCR page sizes)

## Decisions

### Decision 1: Bbox as plain Python class

**Choice:** Convert `Bbox` from `GooCanvas.CanvasGroup` subclass to a plain Python class with explicit parent/children references.

**Rationale:**
- Eliminates per-word GObject creation overhead (~4500 GObjects per page → 0)
- Parent-child hierarchy is already managed manually in GooCanvas (via `add_box()`) — explicit children lists are simpler and faster
- TreeIter, ListIter, to_hocr(), and other traversal logic operate on Python lists, not GooCanvas API — they work unchanged

**Alternatives considered:**
- Keep Bbox as a GObject (without CanvasGroup parent): Still pays PyGObject property overhead for no benefit
- Flat list + depth index: Works for rendering but loses tree structure needed for hOCR export and per-parent child ordering

### Decision 2: Rendering via Cairo in Gtk.DrawingArea draw signal

**Choice:** Connect to the Gtk.DrawingArea `draw` signal (GTK3) and render the scene graph using Cairo + PangoCairo.

**Rationale:**
- Follows the exact same pattern as ImageView — proven in this codebase
- Cairo is already a dependency (`pycairo` in pyproject.toml)
- One `draw` call replaces ~1500 individual GooCanvas item draw calls
- No scene graph management overhead during redraws

**Alternatives considered:**
- GtkSnapshot: GTK4-only, can't use on GTK3
- Retained-mode goocanvas replacement: Already proven too slow

### Decision 3: Scene graph stored in Canvas, drawn by iteration

**Choice:** Canvas owns a tree of Bbox objects (root CanvasGroup → Bbox children). The draw function performs a depth-first traversal, drawing each Bbox as it visits it.

**Rationale:**
- to_hocr() already does depth-first traversal of the same tree
- Confidence index and position index already operate on flattened lists derived from the tree
- The tree is built once in `set_text()` and only modified during edits (add_box/delete_box/update_box)

### Decision 4: Hit testing via linear scan of visible items

**Choice:** On `button-press-event`, iterate the Bbox tree and find the deepest leaf whose bounding rectangle contains the event coordinates.

**Rationale:**
- 1500 words × bounding box check = microseconds in Python
- No spatial index complexity needed at this scale
- GooCanvas's `get_item_at()` also did scene graph traversal

**Alternatives considered:**
- Quadtree: Overkill for typical OCR page sizes (hundreds to low thousands of items)
- Grid index: Could be added later if profiling shows a need

### Decision 5: Text rendering with pre-built PangoCairo layouts

**Choice:** During `set_text()`, pre-build a PangoLayout for each word with the correct font, size, and rotation. Cache it on the Bbox. The draw function calls `pangocairo.show_layout()`.

**Rationale:**
- GooCanvas built a fresh PangoLayout per word at draw time — pre-building avoids that cost
- Rotation is handled via `cairo_matrix_t` on the Cairo context before drawing each word
- Confidence color changes (rare) can regenerate the layout

**Alternatives considered:**
- Create PangoLayout on demand in draw: Simpler but repeats GooCanvas's expensive pattern
- Single PangoLayout with markup: Doesn't support per-word positioning/rotation/coloring

### Decision 6: keep `MockCanvas(Gtk.DrawingArea)` as-is for test_app_window

**Choice:** The existing MockCanvas in `test_app_window.py` already subclasses `Gtk.DrawingArea` and passes the zoom/offset/clear_text contract. No changes needed.

### Decision 7: Batch text loading kept but simplified

**Choice:** Keep the batched idle_add pattern for `set_text()` but simplify — instead of creating GObjects, just prep Bbox data objects and PangoLayouts in batches, then trigger a single queue_draw() at the end.

**Rationale:**
- Still need to avoid blocking the UI during large page loads
- Bbox data object creation is much cheaper than GooCanvas item creation
- The batch size can be increased significantly (GooCanvas had BATCH_SIZE=100 to limit GObject creation overhead — Cairo Bbox creation is faster)

## Risks / Trade-offs

- **GTK3 draw signal vs GTK4 snapshot**: The draw signal (`connect("draw", ...)`) is a GTK3 pattern. When migrating to GTK4, this needs to change to `do_snapshot()`. Mitigation: The drawing code (Cairo operations) stays the same — only the entry point changes. Isolate the drawing logic into a `_draw_scene(ctx)` method that both GTK3's draw signal and GTK4's snapshot callback can call.

- **PangoLayout caching memory**: Pre-building layouts for 1500 words uses more memory than GooCanvas's on-demand approach. Mitigation: Words average ~5 characters — each PangoLayout is small. Total is well under 1MB.

- **Loss of GooCanvas CSS styling**: The current canvas has `self.set_name("scantpaper-ocr-canvas")` for CSS access. Mitigation: Gtk.DrawingArea supports CSS styling via the same mechanism. The name property is preserved.

- **Bbox integration with TreeIter/ListIter**: These classes access Bbox data directly (bbox.type, bbox.confidence, bbox.get_children(), bbox.parent). As long as Bbox retains these attributes, no changes needed.
