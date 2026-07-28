## 1. Convert Bbox to Plain Python Class

- [ ] 1.1 Convert Bbox from `GooCanvas.CanvasGroup` subclass to a plain Python class with explicit `parent` and `children` attributes
- [ ] 1.2 Replace GObject properties with plain attributes (text, bbox, canvas, transformation, confidence, textangle, type, id, baseline)
- [ ] 1.3 Replace GObject signals with a simple callback mechanism (text-changed, bbox-changed, clicked)
- [ ] 1.4 Implement `__init__` to accept all keyword args, store attributes, and initialize parent/children
- [ ] 1.5 Implement `get_children()` to return `self.children` list filtered to Bbox instances
- [ ] 1.6 Implement `get_n_children()` / `get_child(i)` to mirror GooCanvas API for TreeIter compatibility
- [ ] 1.7 Implement `get_box_widget()` / `get_text_widget()` returning None (editing uses coordinates, not widgets)
- [ ] 1.8 Implement `get_centroid()` and `get_position_index()` (positional sorting within parent)
- [ ] 1.9 Implement `walk_children()` for recursive traversal
- [ ] 1.10 Implement `to_hocr()` (unchanged logic — already operates on data attributes)
- [ ] 1.11 Port `confidence2color()` to use the Canvas color lookup table (no GooCanvas dependency)
- [ ] 1.12 Port `update_box()` and `delete_box()` to operate on plain data model and trigger canvas redraw

## 2. Convert Canvas to Gtk.DrawingArea

- [ ] 2.1 Change Canvas to subclass `Gtk.DrawingArea` instead of `GooCanvas.Canvas`
- [ ] 2.2 Add GObject properties: `zoom` (float), `offset` (Gdk.Rectangle), `max_color`/`min_color` (str), `max_confidence`/`min_confidence` (int)
- [ ] 2.3 Implement `__gsignals__` for "zoom-changed" and "offset-changed"
- [ ] 2.4 Port `set_redraw_on_allocate`, `queue_draw`, and drawing cycle from GooCanvas to Gtk.DrawingArea
- [ ] 2.5 Port `zoom` getter/setter (clamp to MIN_ZOOM/MAX_ZOOM, emit signal)
- [ ] 2.6 Port `offset` getter/setter (clamp to pixbuf bounds, emit signal)
- [ ] 2.7 Port `set_text()` — accept bboxes list, build Bbox tree, trigger batched idle_add
- [ ] 2.8 Port `_boxed_text()` — iterate bboxes, create Bbox data objects (no GooCanvas items), batch via idle_add
- [ ] 2.9 Port `clear_text()` — clear Bbox tree, reset pixbuf size and color lookup table
- [ ] 2.10 Port `get_pixbuf_size()` and `get_bbox_at()` with linear scan hit testing
- [ ] 2.11 Implement `set_root_item()` / `get_root_item()` for Bbox tree access

## 3. Implement Cairo Rendering

- [ ] 3.1 Connect to Gtk.DrawingArea `draw` signal (GTK3)
- [ ] 3.2 Implement `_draw_scene(ctx)` — apply zoom and offset transforms, then iterate Bbox tree
- [ ] 3.3 Render bounding boxes: for each Bbox, draw `cairo.rectangle()` with confidence color
- [ ] 3.4 Render text: for each word Bbox with text, create PangoLayout, apply rotation via `cairo_matrix_t`, call `pangocairo.show_layout()`
- [ ] 3.5 Implement PangoLayout caching — pre-build layouts in `set_text()/add_box()`
- [ ] 3.6 Implement confidence color lookup table (same pre-calculated band approach as current code)
- [ ] 3.7 Handle edge cases: empty text (skip text rendering), zero-width words (skip rendering), rotation at various angles
- [ ] 3.8 Isolate drawing into `_draw_scene(ctx)` method callable from both draw signal and future GTK4 snapshot

## 4. Implement Event Handling

- [ ] 4.1 Connect `button-press-event`, `button-release-event`, `motion-notify-event`, `scroll-event`
- [ ] 4.2 Implement middle-click drag pan (store drag start in image coords, adjust offset on motion)
- [ ] 4.3 Implement scroll zoom centered on cursor position (same logic as current `_scroll`)
- [ ] 4.4 Implement cursor management (grabbing cursor during drag, default cursor otherwise)
- [ ] 4.5 Ensure event propagation compatibility with app_window's right-click handler (`_handle_clicks` checks event.button == 3)

## 5. Update Tests

- [ ] 5.1 Rewrite `test_7_canvas.py` — replace all GooCanvas-dependent setup with canvas widget creation using Gtk.DrawingArea
- [ ] 5.2 Test color conversion functions (rgb2hsv, hsv2rgb, string2rgb) — unchanged, just ensure imports work
- [ ] 5.3 Test Canvas as Gtk.DrawingArea: zoom, offset, clear_text, get_pixbuf_size
- [ ] 5.4 Test Bbox creation and tree operations (parent/child, add/remove, get_children)
- [ ] 5.5 Test rendering: create canvas, call set_text, verify queue_draw was triggered (mock draw signal)
- [ ] 5.6 Test hit testing: add bboxes, verify get_bbox_at returns correct item
- [ ] 5.7 Test text editing: update_box, delete_box, add_box
- [ ] 5.8 Test hOCR export: verify output format
- [ ] 5.9 Test confidence indexing: ListIter operations with plain Bbox objects
- [ ] 5.10 Test position indexing: TreeIter operations with plain Bbox objects (parent/child navigation)
- [ ] 5.11 Test event handlers: simulate mouse events, verify zoom/offset changes

## 6. Remove GooCanvas Dependencies

- [ ] 6.1 Remove `gi.require_version("GooCanvas", "2.0")` from `canvas.py`
- [ ] 6.2 Remove `gi.repository.GooCanvas` import from `canvas.py`
- [ ] 6.3 Remove `gi.require_version("GooCanvas", "2.0")` from `test_7_canvas.py`
- [ ] 6.4 Remove `gi.repository.GooCanvas` import from `test_7_canvas.py`
- [ ] 6.5 Remove `gir1.2-goocanvas-2.0` from `.github/workflows/test.yml`
- [ ] 6.6 Remove `gir1.2-goocanvas-2.0` from `.github/workflows/deb.yml`
- [ ] 6.7 Remove `gir1.2-goocanvas-2.0` from `README.md`
- [ ] 6.8 Remove `gir1.2-goocanvas-2.0` from Debian packaging control files

## 7. Verify

- [ ] 7.1 Run `pytest` and confirm all tests pass
- [ ] 7.2 Run `black` and confirm formatting is clean
- [ ] 7.3 Run `pylint` and confirm score is not degraded
- [ ] 7.4 Verify test coverage meets the 98% threshold
