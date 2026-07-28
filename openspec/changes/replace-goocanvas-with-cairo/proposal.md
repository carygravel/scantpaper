## Why

GooCanvas has no GTK4 port and is effectively unmaintained. It's also the performance bottleneck for pages with dense OCR text — the per-word GObject overhead (CanvasGroup + CanvasRect + CanvasText) causes visible lag. Replacing it with a hand-rolled Gtk.DrawingArea + Cairo eliminates both the GTK4 migration blocker and the performance issue in one change.

The codebase already has the pattern: `ImageView` is a `Gtk.DrawingArea` subclass with Cairo rendering, zoom, pan, offset, tools, and event handling. The Canvas replacement follows the same architecture.

## What Changes

- **Replace `GooCanvas.Canvas` subclass** with a `Gtk.DrawingArea` subclass that renders OCR bounding boxes, text, and annotations directly via Cairo
- **Replace `Bbox(GooCanvas.CanvasGroup)`** with a plain Python data object (no GObject) containing rectangle, text, confidence, and hierarchy info
- **Eliminate `GooCanvas.CanvasRect` and `GooCanvas.CanvasText`** — bounding boxes become `cairo.rectangle()` calls, text becomes `pangocairo.show_layout()` calls
- **Remove GooCanvas GIR dependency** from `canvas.py`, tests, CI, packaging, and README
- **No API changes** at the `app_window.py` level — the `Canvas` class retains `zoom`, `offset`, `set_text()`, `clear_text()`, `sort_by_confidence()`, `sort_by_position()`, and signal interfaces

## Capabilities

### New Capabilities
- `canvas-widget`: A Gtk.DrawingArea subclass that renders an OCR scene graph (page → carea → para → line → word) using Cairo, with hit testing, confidence-colored bounding boxes, rotated text, and event handling for text editing

### Modified Capabilities
- None — canvas rendering is purely an implementation detail, no spec-level requirements change

## Impact

- **`scantpaper/canvas.py`**: Full rewrite (~400 lines replaces ~1580 lines). Removes GooCanvas imports, replaces with Gtk.DrawingArea + Cairo + PangoCairo
- **`scantpaper/tests/test_7_canvas.py`**: ~1960 lines of GooCanvas-dependent tests rewritten to test Cairo rendering, hit testing, and scene graph operations without GooCanvas
- **`scantpaper/tests/test_app_window.py`**: Minor — `MockCanvas(Gtk.DrawingArea)` already works but may need adjustment
- **`pyproject.toml`**: No dependency change (PyCairo already listed, PyGObject already listed)
- **`README.md`, CI workflows, deb packaging**: Remove `gir1.2-goocanvas-2.0` references
- **`scantpaper/app_window.py`**: Minimal changes — bind_property still works with Gtk.DrawingArea
