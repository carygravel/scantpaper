## 1. Convert Bbox to Plain Python Class

- [x] 1.1 Convert Bbox from `GooCanvas.CanvasGroup` subclass to a plain Python class with explicit `parent` and `children` attributes
- [x] 1.2 Replace GObject properties with plain attributes (text, bbox, canvas, transformation, confidence, textangle, type, id, baseline)
- [x] 1.3 Replace GObject signals with a simple callback mechanism (text-changed, bbox-changed, clicked)
- [x] 1.4 Implement `__init__` to accept all keyword args, store attributes, and initialize parent/children
- [x] 1.5 Implement `get_children()` to return `self.children` list filtered to Bbox instances
- [x] 1.6 Implement `get_n_children()` / `get_child(i)` to mirror GooCanvas API for TreeIter compatibility
- [x] 1.7 Implement `get_box_widget()` / `get_text_widget()` returning None (editing uses coordinates, not widgets)
- [x] 1.8 Implement `get_centroid()` and `get_position_index()` (positional sorting within parent)
- [x] 1.9 Implement `walk_children()` for recursive traversal
- [x] 1.10 Implement `to_hocr()` (unchanged logic — already operates on data attributes)
- [x] 1.11 Port `confidence2color()` to use the Canvas color lookup table (no GooCanvas dependency)
- [x] 1.12 Port `update_box()` and `delete_box()` to operate on plain data model and trigger canvas redraw

## 2. Convert Canvas to Gtk.DrawingArea

- [x] 2.1 Change Canvas to subclass `Gtk.DrawingArea` instead of `GooCanvas.Canvas`
- [x] 2.2 Add GObject properties: `zoom` (float), `offset` (Gdk.Rectangle), `max_color`/`min_color` (str), `max_confidence`/`min_confidence` (int)
- [x] 2.3 Implement `__gsignals__` for "zoom-changed" and "offset-changed"
- [x] 2.4 Port `set_redraw_on_allocate`, `queue_draw`, and drawing cycle from GooCanvas to Gtk.DrawingArea
- [x] 2.5 Port `zoom` getter/setter (clamp to MIN_ZOOM/MAX_ZOOM, emit signal)
- [x] 2.6 Port `offset` getter/setter (clamp to pixbuf bounds, emit signal)
- [x] 2.7 Port `set_text()` — accept bboxes list, build Bbox tree, trigger batched idle_add
- [x] 2.8 Port `_boxed_text()` — iterate bboxes, create Bbox data objects (no GooCanvas items), batch via idle_add
- [x] 2.9 Port `clear_text()` — clear Bbox tree, reset pixbuf size and color lookup table
- [x] 2.10 Port `get_pixbuf_size()` and `get_bbox_at()` with linear scan hit testing
- [x] 2.11 Implement `set_root_item()` / `get_root_item()` for Bbox tree access

## 3. Implement Cairo Rendering

- [x] 3.1 Connect to Gtk.DrawingArea `draw` signal (GTK3)
- [x] 3.2 Implement `_draw_scene(ctx)` — apply zoom and offset transforms, then iterate Bbox tree
- [x] 3.3 Render bounding boxes: for each Bbox, draw `cairo.rectangle()` with confidence color
- [x] 3.4 Render text: for each word Bbox with text, create PangoLayout, apply rotation via `cairo_matrix_t`, call `pangocairo.show_layout()`
- [x] 3.5 Implement PangoLayout caching — pre-build layouts in `set_text()/add_box()`
- [x] 3.6 Implement confidence color lookup table (same pre-calculated band approach as current code)
- [x] 3.7 Handle edge cases: empty text (skip text rendering), zero-width words (skip rendering), rotation at various angles
- [x] 3.8 Isolate drawing into `_draw_scene(ctx)` method callable from both draw signal and future GTK4 snapshot

## 4. Implement Event Handling

- [x] 4.1 Connect `button-press-event`, `button-release-event`, `motion-notify-event`, `scroll-event`
- [x] 4.2 Implement middle-click drag pan (store drag start in image coords, adjust offset on motion)
- [x] 4.3 Implement scroll zoom centered on cursor position (same logic as current `_scroll`)
- [x] 4.4 Implement cursor management (grabbing cursor during drag, default cursor otherwise)
- [x] 4.5 Ensure event propagation compatibility with app_window's right-click handler (`_handle_clicks` checks event.button == 3)

## 5. Update Tests

- [x] 5.1 Rewrite `test_7_canvas.py` — replace all GooCanvas-dependent setup with canvas widget creation using Gtk.DrawingArea
- [x] 5.2 Test color conversion functions (rgb2hsv, hsv2rgb, string2rgb) — unchanged, just ensure imports work
- [x] 5.3 Test Canvas as Gtk.DrawingArea: zoom, offset, clear_text, get_pixbuf_size
- [x] 5.4 Test Bbox creation and tree operations (parent/child, add/remove, get_children)
- [x] 5.5 Test rendering: create canvas, call set_text, verify queue_draw was triggered (mock draw signal)
- [x] 5.6 Test hit testing: add bboxes, verify get_bbox_at returns correct item
- [x] 5.7 Test text editing: update_box, delete_box, add_box
- [x] 5.8 Test hOCR export: verify output format
- [x] 5.9 Test confidence indexing: ListIter operations with plain Bbox objects
- [x] 5.10 Test position indexing: TreeIter operations with plain Bbox objects (parent/child navigation)
- [x] 5.11 Test event handlers: simulate mouse events, verify zoom/offset changes

## 6. Remove GooCanvas Dependencies

- [x] 6.1 Remove `gi.require_version("GooCanvas", "2.0")` from `canvas.py`
- [x] 6.2 Remove `gi.repository.GooCanvas` import from `canvas.py`
- [x] 6.3 Remove `gi.require_version("GooCanvas", "2.0")` from `test_7_canvas.py`
- [x] 6.4 Remove `gi.repository.GooCanvas` import from `test_7_canvas.py`
- [x] 6.5 Remove `gir1.2-goocanvas-2.0` from `.github/workflows/test.yml`
- [x] 6.6 Remove `gir1.2-goocanvas-2.0` from `.github/workflows/deb.yml`
- [x] 6.7 Remove `gir1.2-goocanvas-2.0` from `README.md`
- [x] 6.8 Remove `gir1.2-goocanvas-2.0` from Debian packaging control files

## 7. Verify

- [x] 7.1 Run `pytest` and confirm all tests pass
- [x] 7.2 Run `black` and confirm formatting is clean
- [x] 7.3 Run `pylint` and confirm score is not degraded
- [x] 7.4 Verify test coverage meets the 98% threshold
