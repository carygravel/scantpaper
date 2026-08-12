"Test Canvas class"

import json
import tempfile
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import cairo
import gi
import pytest
from bboxtree import Bboxtree
from canvas import (
    EMPTY_LIST,
    HOCR_HEADER,
    MAX_ZOOM,
    NOT_FOUND,
    Bbox,
    Canvas,
    ListIter,
    Rectangle,
    TreeIter,
    button_press_callback,
    hsv2rgb,
    rgb2hsv,
    string2rgb,
)
from page import Page

gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import (  # pylint: disable=wrong-import-position,no-name-in-module
    Gdk,
    GLib,
    Pango,
    PangoCairo,
)
from loop_helpers import safe_mainloop


def assert_rgba_equal(c1, c2):
    "Assert two Gdk.RGBA colors are equal"
    assert c1.red == pytest.approx(c2.red)
    assert c1.green == pytest.approx(c2.green)
    assert c1.blue == pytest.approx(c2.blue)


def test_color_functions_more():
    "Test more branches in color conversion"
    # rgb2hsv gray case (delta < tolerance)
    assert rgb2hsv(Gdk.RGBA(0.5, 0.5, 0.5)) == {"h": 0, "s": 0, "v": 0.5}

    # rgb2hsv green sector
    res = rgb2hsv(Gdk.RGBA(0.1, 0.8, 0.1))
    assert res["h"] == pytest.approx(120)

    # rgb2hsv blue sector
    res = rgb2hsv(Gdk.RGBA(0.1, 0.1, 0.8))
    assert res["h"] == pytest.approx(240)

    # rgb2hsv negative hue wrap
    # (rgb.green - rgb.blue) / delta * 60
    # if red is max, green < blue
    res = rgb2hsv(Gdk.RGBA(0.8, 0.1, 0.2))
    # delta = 0.7. (0.1-0.2)/0.7 * 60 = -8.57. wrap to 351.43
    assert res["h"] == pytest.approx(360 - 60 * 0.1 / 0.7)

    # hsv2rgb sectors
    # already has some but let's be sure
    # Sector 2: red=p, green=v, blue=t
    c = hsv2rgb({"h": 120, "s": 1.0, "v": 1.0})
    assert_rgba_equal(c, Gdk.RGBA(0, 1, 0))

    # Sector 3: red=p, green=q, blue=v
    c = hsv2rgb({"h": 180, "s": 1.0, "v": 1.0})
    assert_rgba_equal(c, Gdk.RGBA(0, 1, 1))

    # Sector 4: red=t, green=p, blue=v
    c = hsv2rgb({"h": 240, "s": 1.0, "v": 1.0})
    assert_rgba_equal(c, Gdk.RGBA(0, 0, 1))

    # Else sector: red=v, green=p, blue=q
    c = hsv2rgb({"h": 300, "s": 1.0, "v": 1.0})
    assert_rgba_equal(c, Gdk.RGBA(1, 0, 1))


def test_string2rgb():
    "Test string2rgb color parsing"
    # named color
    c = string2rgb("red")
    assert c.red == 1.0
    assert c.green == 0.0
    assert c.blue == 0.0
    assert c.alpha == 1.0

    # hex color
    c = string2rgb("#00ff00")
    assert c.red == 0.0
    assert c.green == 1.0
    assert c.blue == 0.0
    assert c.alpha == 1.0

    # rgba with alpha
    c = string2rgb("rgba(0, 0, 255, 0.5)")
    assert c.red == 0.0
    assert c.green == 0.0
    assert c.blue == 1.0
    assert c.alpha == 0.5

    # rgb() syntax
    c = string2rgb("rgb(255, 128, 0)")
    assert c.red == 1.0
    assert c.green == pytest.approx(128.0 / 255.0)
    assert c.blue == 0.0
    assert c.alpha == 1.0


def get_bboxes_and_indices(json_string):
    "Helper to simulate docthread parsing"
    tree = Bboxtree(json_string)
    bboxes = list(tree.each_bbox())
    words = []
    for i, box in enumerate(bboxes):
        if box.get("type") == "word" and len(box.get("text", "")) > 0:
            words.append((i, box.get("confidence", 100)))
    words.sort(key=lambda x: x[1])
    return bboxes, [x[0] for x in words]


def test_canvas_offset_setter_no_change(mocker):
    "Test offset setter when values don't change"
    canvas_obj = Canvas()
    canvas_obj.emit = MagicMock()

    rect = Gdk.Rectangle()
    rect.x = 0
    rect.y = 0
    canvas_obj.offset = rect

    canvas_obj.emit.reset_mock()
    canvas_obj.offset = rect
    canvas_obj.emit.assert_not_called()


def test_hsv2rgb_coverage():
    "Test hsv2rgb all branches"
    # s=0
    assert hsv2rgb({"h": 0, "s": 0, "v": 1.0}).red == 1.0

    # sectors
    def check_sector(h, r, g, b):
        c = hsv2rgb({"h": h, "s": 1.0, "v": 1.0})
        assert c.red == pytest.approx(r)
        assert c.green == pytest.approx(g)
        assert c.blue == pytest.approx(b)

    check_sector(0, 1, 0, 0)  # i=0
    check_sector(60, 1, 1, 0)  # i=1 (yellow)
    check_sector(120, 0, 1, 0)  # i=2 (green)
    check_sector(180, 0, 1, 1)  # i=3 (cyan)
    check_sector(240, 0, 0, 1)  # i=4 (blue)
    check_sector(300, 1, 0, 1)  # i=5 (magenta)


def test_canvas_basics(rose_pnm):
    "Basic tests"
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=72,
            dir=dirname,
        )
        page.import_hocr(HOCR_HEADER + """ <body>
  <div class='ocr_page' id='page_1' title='image "test.tif"; bbox 0 0 422 61'>
   <div class='ocr_carea' id='block_1_1' title="bbox 1 14 420 59">
    <p class='ocr_par'>
     <span class='ocr_line' id='line_1_1' title="bbox 1 14 420 59">
      <span class='ocr_word' id='word_1_1' title="bbox 1 14 77 48">
       <span class='xocr_word' id='xword_1_1' title="x_wconf 3">The—</span>
      </span>
      <span class='ocr_word' id='word_1_2' title="bbox 92 14 202 48">
       <span class='xocr_word' id='xword_1_2' title="x_wconf 74">quick</span>
      </span>
      <span class='ocr_word' id='word_1_3' title="bbox 214 14 341 48">
       <span class='xocr_word' id='xword_1_3' title="x_wconf 75">brown</span>
      </span>
      <span class='ocr_word' id='word_1_4' title="bbox 250 14 420 48">
       <span class='xocr_word' id='xword_1_4' title="x_wconf 71">fox</span>
      </span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
""")

        canvas = Canvas()
        canvas.sort_by_confidence()
        mlp = safe_mainloop(2000)
        bboxes, indices = get_bboxes_and_indices(page.text_layer)
        canvas.set_text(
            bboxes=bboxes,
            sorted_word_indices=indices,
            finished_callback=lambda: mlp.quit(),
        )
        mlp.run()

        bbox = canvas.get_first_bbox()
        assert bbox.text == "The—", "get_first_bbox"
        canvas.set_index_by_bbox(bbox)
        bbox = canvas.get_next_bbox()
        assert bbox.text == "fox", "get_next_bbox"
        assert canvas.get_previous_bbox().text == "The—", "get_previous_text"
        bbox = canvas.get_last_bbox()
        assert bbox.text == "brown", "get_last_text"

        bbox.delete_box()
        assert canvas.get_last_bbox().text == "quick", "get_last_bbox after deletion"


def test_canvas_basics2(rose_pnm):
    "Basic tests"
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=72,
            dir=dirname,
        )
        page.import_hocr(HOCR_HEADER + """ <body>
  <div class='ocr_page' id='page_1' title='image "test.tif"; bbox 0 0 422 61'>
   <div class='ocr_carea' id='block_1_1' title="bbox 1 14 420 59">
    <p class='ocr_par'>
     <span class='ocr_line' id='line_1_1' title="bbox 1 14 420 59">
      <span class='ocr_word' id='word_1_1' title="bbox 1 14 77 48">
       <span class='xocr_word' id='xword_1_1' title="x_wconf 3">The—</span>
      </span>
      <span class='ocr_word' id='word_1_2' title="bbox 92 14 202 48">
       <span class='xocr_word' id='xword_1_2' title="x_wconf 74">quick</span>
      </span>
      <span class='ocr_word' id='word_1_3' title="bbox 214 14 341 48">
       <span class='xocr_word' id='xword_1_3' title="x_wconf 75">brown</span>
      </span>
      <span class='ocr_word' id='word_1_4' title="bbox 250 14 420 48">
       <span class='xocr_word' id='xword_1_4' title="x_wconf 71">fox</span>
      </span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
""")

        canvas = Canvas()
        canvas.sort_by_confidence()
        mlp = safe_mainloop(2000)
        bboxes, indices = get_bboxes_and_indices(page.text_layer)
        canvas.set_text(
            bboxes=bboxes,
            sorted_word_indices=indices,
            finished_callback=lambda: mlp.quit(),
        )
        mlp.run()

        group = canvas.get_first_bbox()

        group.update_box("No", Rectangle(x=2, y=15, width=74, height=32))

        canvas.add_box(text="foo", bbox=Rectangle(x=355, y=15, width=74, height=32))

        expected = HOCR_HEADER + """ <body>
  <div class='ocr_page' id='page_1' title='bbox 0 0 422 61'>
   <div class='ocr_carea' id='block_1_1' title='bbox 1 14 420 59'>
    <span class='ocr_line' id='line_1_1' title='bbox 1 14 420 59'>
     <span class='ocr_word' id='word_1_1' title='bbox 2 15 76 47; x_wconf 100'>No</span>
     <span class='ocr_word' id='word_1_2' title='bbox 92 14 202 48; x_wconf 74'>quick</span>
     <span class='ocr_word' id='word_1_3' title='bbox 214 14 341 48; x_wconf 75'>brown</span>
     <span class='ocr_word' id='word_1_4' title='bbox 250 14 420 48; x_wconf 71'>fox</span>
     <span class='ocr_word'  title='bbox 355 15 429 47; x_wconf 100'>foo</span>
    </span>
   </div>
  </div>
 </body>
</html>
"""

        assert canvas.hocr() == expected, "updated hocr"

        canvas.sort_by_position()
        bbox = canvas.get_first_bbox()
        assert bbox.text == "No", "get_first_bbox position"
        with pytest.raises(StopIteration):
            canvas.get_previous_bbox()
        bbox = canvas.get_next_bbox()
        assert bbox.text == "quick", "get_next_bbox position"
        bbox = canvas.get_previous_bbox()
        assert bbox.text == "No", "get_previous_bbox position"
        bbox = canvas.get_last_bbox()
        assert bbox.text == "foo", "get_last_bbox position"
        with pytest.raises(StopIteration):
            canvas.get_next_bbox()

        #########################

        # v2.10.0 had a bug where adding a word box manually where there was an overlap
        # with another word box picked up the existing word box as the parent.
        # A another bug prevented adding the text '0'
        canvas.add_box(text="0", bbox=Rectangle(x=356, y=15, width=74, height=32))

        expected = HOCR_HEADER + """ <body>
  <div class='ocr_page' id='page_1' title='bbox 0 0 422 61'>
   <div class='ocr_carea' id='block_1_1' title='bbox 1 14 420 59'>
    <span class='ocr_line' id='line_1_1' title='bbox 1 14 420 59'>
     <span class='ocr_word' id='word_1_1' title='bbox 2 15 76 47; x_wconf 100'>No</span>
     <span class='ocr_word' id='word_1_2' title='bbox 92 14 202 48; x_wconf 74'>quick</span>
     <span class='ocr_word' id='word_1_3' title='bbox 214 14 341 48; x_wconf 75'>brown</span>
     <span class='ocr_word' id='word_1_4' title='bbox 250 14 420 48; x_wconf 71'>fox</span>
     <span class='ocr_word'  title='bbox 355 15 429 47; x_wconf 100'>foo</span>
     <span class='ocr_word'  title='bbox 356 15 430 47; x_wconf 100'>0</span>
    </span>
   </div>
  </div>
 </body>
</html>
"""

        assert (
            canvas.hocr() == expected
        ), "the parent of a box should not be of the same class"

        #########################

        canvas.sort_by_confidence()
        canvas.get_last_bbox().update_box(
            "No", Rectangle(x=2, y=15, width=75, height=32)
        )
        assert (
            canvas.get_last_bbox().text == "No"
        ), "don't sort if confidence hasn't changed"

        #########################

        group.confidence = 100
        canvas.max_confidence = 90
        canvas.min_confidence = 50
        assert group.confidence2color() == "black", "> max"
        group.confidence = 70
        # Lookup table quantizes colors into bands
        # Check it's a hex color (not min/max extremes)
        mid_color = group.confidence2color()
        assert mid_color.startswith("#"), "mid way should be hex color"
        assert mid_color not in ["black", "red"], "mid way should not be extreme"
        group.confidence = 40
        assert group.confidence2color() == "red", "< min"

        #########################

        group.update_box("<em>No</em>", Rectangle(x=2, y=15, width=74, height=32))

        expected = HOCR_HEADER + """ <body>
  <div class='ocr_page' id='page_1' title='bbox 0 0 422 61'>
   <div class='ocr_carea' id='block_1_1' title='bbox 1 14 420 59'>
    <span class='ocr_line' id='line_1_1' title='bbox 1 14 420 59'>
     <span class='ocr_word' id='word_1_1' title='bbox 2 15 76 47; x_wconf 100'>&lt;em&gt;No&lt;/em&gt;</span>
     <span class='ocr_word' id='word_1_2' title='bbox 92 14 202 48; x_wconf 74'>quick</span>
     <span class='ocr_word' id='word_1_3' title='bbox 214 14 341 48; x_wconf 75'>brown</span>
     <span class='ocr_word' id='word_1_4' title='bbox 250 14 420 48; x_wconf 71'>fox</span>
     <span class='ocr_word'  title='bbox 355 15 429 47; x_wconf 100'>foo</span>
     <span class='ocr_word'  title='bbox 356 15 430 47; x_wconf 100'>0</span>
    </span>
   </div>
  </div>
 </body>
</html>
"""

        assert canvas.hocr() == expected, "updated hocr with HTML-escape characters"


def test_canvas_clear_text(mocker):
    "Test clearing text from canvas"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas_obj = Canvas()
    canvas_obj._pixbuf_size = {
        "width": 100,
        "height": 100,
    }
    mock_queue_draw = mocker.patch.object(canvas_obj, "queue_draw")

    canvas_obj.clear_text()
    assert canvas_obj.get_pixbuf_size() is None
    assert mock_queue_draw.called


def test_hocr(rose_pnm):
    "Tests hocr export"
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=72,
            dir=dirname,
        )

        page.import_hocr(HOCR_HEADER + """ <body>
  <div class='ocr_page' id='page_1' title='image "test.tif"; bbox 0 0 204 288'>
   <div class='ocr_carea' id='block_1_1' title="bbox 1 14 202 286">
    <p class='ocr_par'>
     <span class='ocr_line' id='line_1_1' title="bbox 1 14 202 59; baseline 0.008 -9 ">
      <span class='ocr_word' id='word_1_1' title="bbox 1 14 77 48">
       <span class='xocr_word' id='xword_1_1' title="x_wconf 3">The</span>
      </span>
      <span class='ocr_word' id='word_1_2' title="bbox 92 14 202 59">
       <span class='xocr_word' id='xword_1_2' title="x_wconf 3">quick</span>
      </span>
     </span>
    </p>
    <p class='ocr_par'>
     <span class='ocr_line' id='line_1_2' title="bbox 1 80 35 286; textangle 90">
      <span class='ocr_word' id='word_1_4' title="bbox 1 80 35 195">
       <span class='xocr_word' id='xword_1_4' title="x_wconf 4">fox</span>
      </span>
      <span class='ocr_word' id='word_1_3' title="bbox 1 159 35 286">
       <span class='xocr_word' id='xword_1_3' title="x_wconf 3">brown</span>
      </span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
""")

        canvas = Canvas()
        mlp = safe_mainloop(2000)
        bboxes, indices = get_bboxes_and_indices(page.text_layer)
        canvas.set_text(
            bboxes=bboxes,
            sorted_word_indices=indices,
            finished_callback=lambda: mlp.quit(),
        )
        mlp.run()
        canvas.sort_by_confidence()

        expected = HOCR_HEADER + """ <body>
  <div class='ocr_page' id='page_1' title='bbox 0 0 204 288'>
   <div class='ocr_carea' id='block_1_1' title='bbox 1 14 202 286'>
    <span class='ocr_line' id='line_1_1' title='bbox 1 14 202 59; baseline 0.008 -9'>
     <span class='ocr_word' id='word_1_1' title='bbox 1 14 77 48; x_wconf 3'>The</span>
     <span class='ocr_word' id='word_1_2' title='bbox 92 14 202 59; x_wconf 3'>quick</span>
    </span>
    <span class='ocr_line' id='line_1_2' title='bbox 1 80 35 286; textangle 90'>
     <span class='ocr_word' id='word_1_4' title='bbox 1 80 35 195; x_wconf 4'>fox</span>
     <span class='ocr_word' id='word_1_3' title='bbox 1 159 35 286; x_wconf 3'>brown</span>
    </span>
   </div>
  </div>
 </body>
</html>
"""

        assert (
            canvas.hocr() == expected
        )  #  'updated hocr with extended hOCR properties'

        #########################

        root = canvas.get_root_item()
        page = root.get_child(0)
        carea = page.get_children()[0]
        # carea children: either [line_1_1, line_1_2] (no para level) or [para1, para2]
        kids = carea.get_children()
        line_1_2 = kids[1]
        bbox = line_1_2.get_children()[1]  # word_1_3

        assert isinstance(bbox, Bbox)
        assert bbox.textangle == 0, "word_1_3's textangle is 0"
        assert bbox.transformation[0] == 90, "word_1_3's (inherited) rotation is 90"

        #########################

        bbox = canvas.get_first_bbox()
        bbox.delete_box()
        bbox = canvas.get_next_bbox()
        bbox.delete_box()
        bbox = canvas.get_next_bbox()
        bbox.delete_box()
        bbox = canvas.get_next_bbox()
        bbox.delete_box()
        with pytest.raises(StopIteration):
            canvas.get_last_bbox()


def test_bbox_text_placement(rose_pnm):
    "Test that hOCR text is placed correctly within its bounding box"
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=72,
            dir=dirname,
        )
        page.import_hocr(HOCR_HEADER + """<body>
<div class='ocr_page' id='page_1' title='image "test.tif"; bbox 0 0 204 288'>
<div class='ocr_carea' id='block_1_1' title="bbox 1 14 202 286">
<p class='ocr_par'>
<span class='ocr_line' id='line_1_1' title="bbox 1 80 35 286">
<span class='ocr_word' id='word_1_1' title="bbox 1 80 35 195">
<span class='xocr_word' id='xword_1_1' title="x_wconf 4">fox</span>
      </span>
     </span>
    </p>
   </div>
  </div>
 </body>
 </html>
 """)
        canvas = Canvas()
        mlp = safe_mainloop(2000)
        bboxes, indices = get_bboxes_and_indices(page.text_layer)
        canvas.set_text(
            bboxes=bboxes,
            sorted_word_indices=indices,
            finished_callback=lambda: mlp.quit(),
        )
        mlp.run()

        # Get the bbox for the word 'fox'
        bbox = canvas.get_first_bbox()
        assert bbox.text == "fox"


def test_initialisation(mocker):
    "Test initialisation"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    assert isinstance(canvas, Canvas)
    assert canvas.max_color == "black", "max-color"
    assert canvas.min_color == "red", "min-color"
    assert canvas.max_confidence == 95, "max-confidence"
    assert canvas.min_confidence == 50, "min-confidence"


def test_drag_text_layer(mocker):
    "Test dragging a text layer"

    @dataclass
    class MockEvent:
        "mock enough of the event class to test it"

        button: int
        x: int
        y: int

    mock_display = mocker.patch("gi.repository.Gdk.Display.get_default")
    mock_display.return_value.get_default_seat.return_value.get_pointer.return_value.get_position.side_effect = [
        (None, 10, 10),
        (None, 20, 20),
    ]
    mocker.patch("gi.repository.Gdk.Cursor.new_from_name")
    canvas = Canvas()
    mock_window = MagicMock()
    canvas.get_window = MagicMock(return_value=mock_window)
    canvas.set_size_request(600, 800)
    page = Bbox(
        canvas=canvas,
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        transformation=[0, 0, 0],
    )
    canvas.set_root_item(page)
    canvas._pixbuf_size = {
        "width": 100,
        "height": 100,
    }

    event = MockEvent(button=2, x=10, y=10)
    canvas._button_pressed(canvas, event)
    event.x = 20
    event.y = 20
    canvas._motion(canvas, event)
    assert canvas.get_offset().x == 0, "canvas has moved"


def test_canvas_drag_cursor(mocker):
    "Test that the cursor changes when dragging the canvas."
    mock_display = mocker.patch("gi.repository.Gdk.Display.get_default")
    mock_display.return_value.get_default_seat.return_value.get_pointer.return_value.get_position.return_value = (
        None,
        10,
        10,
    )
    mock_cursor_new = mocker.patch("gi.repository.Gdk.Cursor.new_from_name")

    canvas = Canvas()
    mock_window = MagicMock()
    # We need to mock get_window() because the canvas is not in a real window
    canvas.get_window = MagicMock(return_value=mock_window)

    # 1. Test button press: cursor should change to "grabbing"
    press_event = MagicMock()
    press_event.button = 2
    canvas._button_pressed(canvas, press_event)

    mock_cursor_new.assert_called_once_with(mocker.ANY, "grabbing")
    mock_window.set_cursor.assert_called_once_with(mock_cursor_new.return_value)

    # 2. Test button release: cursor should change back to default
    mock_window.set_cursor.reset_mock()
    release_event = MagicMock()
    release_event.button = 2
    canvas._button_released(canvas, release_event)

    mock_window.set_cursor.assert_called_once_with(None)


def test_canvas_hocr_empty(mocker):
    "Test Canvas.hocr when empty"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    assert canvas.hocr() == ""


def test_canvas_set_offset_clamping(mocker):
    "Test set_offset clamping logic"
    canvas_obj = Canvas()

    canvas_obj._pixbuf_size = None
    canvas_obj.set_offset(10, 10)
    assert canvas_obj.offset.x == 0 and canvas_obj.offset.y == 0

    canvas_obj._pixbuf_size = {
        "width": 100,
        "height": 100,
    }

    rect = Gdk.Rectangle()
    rect.width = 200
    rect.height = 200
    canvas_obj.get_allocation = MagicMock(return_value=rect)
    canvas_obj._to_image_distance = MagicMock(return_value=(200, 200))
    canvas_obj.get_scale_factor = MagicMock(return_value=1)

    canvas_obj.set_offset(0, 0)
    assert canvas_obj.offset.x == 50
    assert canvas_obj.offset.y == 50

    canvas_obj._pixbuf_size = {
        "width": 300,
        "height": 300,
    }
    canvas_obj._to_image_distance = MagicMock(return_value=(200, 200))

    canvas_obj.set_offset(10, 10)
    assert canvas_obj.offset.x == 0
    assert canvas_obj.offset.y == 0

    canvas_obj.set_offset(-150, -150)
    assert canvas_obj.offset.x == -100
    assert canvas_obj.offset.y == -100


def test_canvas_scroll(mocker):
    "Test scroll event zooming"
    canvas_obj = Canvas()
    canvas_obj.zoom = 1.0

    canvas_obj.get_scale_factor = MagicMock(return_value=1)

    event = MagicMock()
    event.x = 50
    event.y = 50
    event.direction = Gdk.ScrollDirection.UP

    canvas_obj._pixbuf_size = {
        "width": 1000,
        "height": 1000,
    }
    rect = Gdk.Rectangle()
    rect.width = 200
    rect.height = 200
    canvas_obj.get_allocation = MagicMock(return_value=rect)

    with patch.object(
        canvas_obj, "set_offset", wraps=canvas_obj.set_offset
    ) as mock_set_offset:
        canvas_obj._scroll(canvas_obj, event)
        assert canvas_obj.zoom == 2.0
        mock_set_offset.assert_called()

    event.direction = Gdk.ScrollDirection.DOWN
    canvas_obj._scroll(canvas_obj, event)
    assert canvas_obj.zoom == 1.0


def test_canvas_get_bbox_at(mocker):
    "Test get_bbox_at"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()

    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    line = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=20),
        type="line",
        parent=page,
    )

    # get_bbox_at uses _find_bbox_at
    result = canvas_obj.get_bbox_at(Rectangle(x=10, y=10, width=1, height=1))
    assert result == line

    # Case where it returns a word and we want the parent
    word = canvas_obj.add_box(
        text="w", bbox=Rectangle(x=0, y=0, width=10, height=10), parent=line
    )
    result = canvas_obj.get_bbox_at(Rectangle(x=5, y=5, width=1, height=1))
    assert result == line

    # Point outside all boxes
    with pytest.raises(ReferenceError):
        canvas_obj.get_bbox_at(Rectangle(x=200, y=200, width=1, height=1))


def test_rectangle_init():
    "Test Rectangle init checks"
    with pytest.raises(AttributeError):
        Rectangle(x=0, y=0, width=10)


def test_list_iter_edge_cases():
    "Test ListIter edge cases"
    li = ListIter()

    with pytest.raises(StopIteration):
        li.get_current_bbox()

    bbox1 = MagicMock()
    bbox2 = MagicMock()

    li.add_box_to_index(bbox1, 90)
    li.add_box_to_index(bbox2, 80)

    assert li.get_first_bbox() == bbox2
    assert li.get_next_bbox() == bbox1
    assert li.get_previous_bbox() == bbox2
    assert li.get_last_bbox() == bbox1

    li.remove_current_box_from_index()
    assert li.get_current_bbox() == bbox2

    li.remove_current_box_from_index()
    assert len(li.list) == 0

    with patch("canvas.logger") as mock_logger:
        li.add_box_to_index(None, 100)
        mock_logger.warning.assert_called()

        li.insert_after_position(None, 0, 100)
        mock_logger.warning.assert_called()

        li.insert_after_position(bbox1, 100, 100)
        mock_logger.warning.assert_called()


def test_bbox_methods_via_canvas(mocker):
    "Test Bbox methods by creating them on canvas"
    # This avoids segfaults by letting Canvas manage hierarchy
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()

    # 1. Test hierarchy and get_children
    root = canvas_obj.get_root_item()

    # Create 'page'
    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )

    # Create 'parent' (line) attached to page
    parent = canvas_obj.add_box(
        text="parent",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="line",
        parent=page,
    )

    # Add children to parent
    child1 = canvas_obj.add_box(
        text="c1",
        bbox=Rectangle(x=10, y=10, width=10, height=10),
        parent=parent,
    )
    child2 = canvas_obj.add_box(
        text="c2",
        bbox=Rectangle(x=30, y=10, width=10, height=10),
        parent=parent,
    )

    assert parent.get_n_children() >= 2
    children = parent.get_children()
    # Note: get_children filters for Bbox instances. CanvasGroup might contain rect/text items.
    assert len(children) == 2
    assert children[0] == child1
    assert children[1] == child2

    assert parent.get_child_ordinal(child1) >= 0
    assert parent.get_child_ordinal(child2) > parent.get_child_ordinal(child1)

    # 2. Test walk_children
    callback = MagicMock()
    parent.walk_children(callback)
    # child1 and child2 are leaves (words)
    assert callback.call_count == 2
    callback.assert_any_call(child1)
    callback.assert_any_call(child2)

    # 3. Test get_position_index
    assert child1.get_position_index() == 0
    assert child2.get_position_index() == 1


def test_canvas_indices(mocker):
    "Test Canvas indices switching and manipulation"
    canvas_obj = Canvas()

    # Mock indices
    mock_confidence = MagicMock()
    mock_position = MagicMock()
    canvas_obj.confidence_index = mock_confidence
    canvas_obj.position_index = mock_position

    bbox = MagicMock()
    bbox.confidence = 90

    # Mock TreeIter to avoid TypeError: bbox is not a Bbox object
    with patch("canvas.TreeIter") as mock_tree_iter:
        mock_tree_iter.return_value = mock_position

        # Test sort_by_confidence
        canvas_obj.sort_by_confidence()
        assert canvas_obj._current_index == "confidence"

        # Test get_current_bbox delegation
        canvas_obj.get_current_bbox()
        mock_confidence.get_current_bbox.assert_called_once()
        mock_tree_iter.assert_called()

        # Test set_index_by_bbox
        canvas_obj.set_index_by_bbox(bbox)
        mock_confidence.set_index_by_bbox.assert_called_with(bbox, 90)

        # Test set_other_index (swapping)
        canvas_obj.set_other_index(bbox)
        assert canvas_obj.position_index == mock_tree_iter.return_value

        # Test sort_by_position
        canvas_obj.sort_by_position()
        assert canvas_obj._current_index == "position"

        canvas_obj.get_current_bbox()
        mock_position.get_current_bbox.assert_called_once()

        # Test set_index_by_bbox (position)
        canvas_obj.set_index_by_bbox(bbox)
        assert canvas_obj.position_index == mock_tree_iter.return_value

        # Test set_other_index (swapping back to confidence)
        canvas_obj.set_other_index(bbox)
        mock_confidence.set_index_by_bbox.assert_called_with(bbox, 90)


def test_bbox_stack_index(mocker):
    "Test get_stack_index_by_position logic"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()

    page = canvas_obj.add_box(
        text="page",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )

    parent = canvas_obj.add_box(
        text="parent",
        bbox=Rectangle(x=0, y=0, width=100, height=20),
        type="line",
        parent=page,
    )

    # No internal Rect/Text children in Cairo implementation
    assert parent.get_n_children() == 0

    canvas_obj.add_box(
        text="c1", bbox=Rectangle(x=10, y=0, width=10, height=10), parent=parent
    )
    canvas_obj.add_box(
        text="c3", bbox=Rectangle(x=50, y=0, width=10, height=10), parent=parent
    )

    # Children: c1(centroid x=15), c3(centroid x=55)
    new_bbox = MagicMock()
    new_bbox.get_centroid.return_value = (35, 5)  # between c1(15) and c3(55)

    idx = parent.get_stack_index_by_position(new_bbox)
    assert idx == 1


def test_add_box_callbacks(mocker):
    "Test add_box with callbacks and transformation"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()

    page = canvas_obj.add_box(
        text="page",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )

    mock_edit = MagicMock()
    parent = canvas_obj.add_box(
        text="parent",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        parent=page,
        textangle=10,
    )

    child = canvas_obj.add_box(
        text="child",
        bbox=Rectangle(x=10, y=10, width=20, height=20),
        edit_callback=mock_edit,
        parent=parent,
    )

    event = MagicMock()
    event.button = 1
    # Call callback directly to avoid GdkEvent conversion issues in tests
    button_press_callback(child, None, event, mock_edit)
    mock_edit.assert_called_once()


def test_bbox_init_zero_width_text(mocker):
    "Test Bbox init with zero width text"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="page",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )

    with patch("canvas.logger") as mock_logger:
        bbox = canvas_obj.add_box(
            text="zerowidth",
            bbox=Rectangle(x=0, y=0, width=10, height=10),
            parent=page,
        )
        # In Cairo implementation, zero-width text just gets a Pango layout
        # No GooCanvas error is emitted
        assert bbox.text == "zerowidth"


def test_tree_iter_navigation(mocker):
    "Test TreeIter navigation methods"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()

    # Create page without text to keep it simple (no internal Text child)
    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    # line without text
    line = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=20),
        type="line",
        parent=page,
    )
    w1 = canvas_obj.add_box(
        text="word1",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        type="word",
        parent=line,
    )
    w2 = canvas_obj.add_box(
        text="word2",
        bbox=Rectangle(x=20, y=0, width=10, height=10),
        type="word",
        parent=line,
    )

    # Test full navigation from page
    ti = TreeIter(page)
    assert ti.get_current_bbox() == page
    assert ti.next_bbox() == line
    assert ti.next_bbox() == w1
    assert ti.next_bbox() == w2
    with pytest.raises(StopIteration):
        ti.next_bbox()

    assert ti.previous_bbox() == w1
    assert ti.previous_bbox() == line
    assert ti.previous_bbox() == page
    with pytest.raises(StopIteration):
        ti.previous_bbox()

    ti = TreeIter(w2)
    assert ti.first_word() == w1
    assert ti.last_word() == w2

    ti = TreeIter(w1)
    assert ti.next_word() == w2
    with pytest.raises(StopIteration):
        ti.next_word()


def test_bbox_to_hocr_types(mocker):
    "Test Bbox.to_hocr with different types"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="page",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )

    carea = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=50, height=50),
        type="carea",
        parent=page,
    )
    para = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=40, height=40),
        type="para",
        parent=carea,
    )

    hocr = carea.to_hocr()
    assert "ocr_carea" in hocr
    assert "<div" in hocr

    hocr = para.to_hocr()
    assert "ocr_par" in hocr
    assert "<p" in hocr


def test_canvas_event_handlers(mocker):
    "Test Canvas event handlers for coverage"
    mock_display = MagicMock(spec=Gdk.Display)
    mocker.patch("gi.repository.Gdk.Display.get_default", return_value=mock_display)

    canvas_obj = Canvas()
    canvas_obj._device = MagicMock()
    canvas_obj._device.get_position.return_value = (None, 100, 100)
    canvas_obj.get_window = MagicMock()

    # _button_pressed
    event = MagicMock()
    event.button = 2

    with patch("gi.repository.Gdk.Cursor.new_from_name") as mock_cursor_new:
        canvas_obj._button_pressed(None, event)
        assert canvas_obj._dragging
        assert canvas_obj._drag_start == {"x": 100, "y": 100}
        mock_cursor_new.assert_called()

    # _motion: zoom is used in drag calculation
    canvas_obj.get_offset = MagicMock(return_value=Gdk.Rectangle())
    canvas_obj._device.get_position.return_value = (None, 110, 110)
    canvas_obj.set_offset = MagicMock()

    canvas_obj._motion(None, None)
    canvas_obj.set_offset.assert_called()

    # _button_released
    canvas_obj._button_released(None, event)
    assert not canvas_obj._dragging


def test_bbox_update_box_empty_text(mocker):
    "Test Bbox.update_box with empty text (deletes box)"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="page",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    line = canvas_obj.add_box(
        text="line",
        bbox=Rectangle(x=0, y=0, width=100, height=20),
        type="line",
        parent=page,
    )
    word = canvas_obj.add_box(
        text="word",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        type="word",
        parent=line,
    )

    canvas_obj.position_index = MagicMock()
    word.delete_box = MagicMock()
    word.update_box("", Rectangle(x=0, y=0, width=10, height=10))
    word.delete_box.assert_called_once()


def test_list_iter_more(mocker):
    "Test ListIter additional methods"
    li = ListIter()
    bbox = MagicMock()
    li.add_box_to_index(bbox, 50)

    li.insert_before_position(bbox, 0, 40)
    assert len(li.list) == 2
    assert li.list[0][1] == 40

    li.insert_after_position(bbox, 1, 60)
    assert len(li.list) == 3
    assert li.list[2][1] == 60

    # Test set_index_by_bbox with multiple same values
    bbox2 = MagicMock()
    li.add_box_to_index(bbox2, 50)
    li.set_index_by_bbox(bbox2, 50)
    assert li.list[li.index][0] == bbox2


def test_tree_iter_exceptions(mocker):
    "Test TreeIter exceptions"

    # Init with non-Bbox
    with pytest.raises(TypeError):
        TreeIter("not-a-bbox")

    # Setup a simple tree
    canvas_obj = Canvas()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    ti = TreeIter(page)

    # next_bbox on leaf/empty
    with pytest.raises(StopIteration):
        ti.next_bbox()

    # previous_bbox on root
    with pytest.raises(StopIteration):
        ti.previous_bbox()

    # previous_word with no words
    with pytest.raises(StopIteration):
        ti.previous_word()


def test_bbox_update_box_full(mocker):
    "Test Bbox.update_box with more branches"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="page",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    line = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=20),
        type="line",
        parent=page,
    )
    word = canvas_obj.add_box(
        text="old",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        type="word",
        parent=line,
    )

    # Update with new text and position
    new_selection = Rectangle(x=5, y=5, width=15, height=15)
    word.update_box("new", new_selection)

    assert word.text == "new"
    assert word.confidence == 100
    assert word.bbox.x == 5

    # Update with same text but different position to trigger move_child branch
    # We need another child to see ordering change
    word2 = canvas_obj.add_box(
        text="word2", bbox=Rectangle(x=30, y=0, width=10, height=10), parent=line
    )
    # word is at x=5, word2 at x=30.
    # Move word to x=40 (after word2)
    word.update_box("new", Rectangle(x=40, y=5, width=15, height=15))
    # word centroid x: 40 + 7.5 = 47.5
    # word2 centroid x: 30 + 5 = 35.
    # visually word2 < word
    assert word2.get_centroid()[0] < word.get_centroid()[0]


def test_canvas_set_text_full(mocker, rose_pnm):
    "Test Canvas.set_text with real-ish page"
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=72,
            dir=dirname,
        )
        page.text_layer = json.dumps(
            [
                {
                    "depth": 0,
                    "bbox": (0, 0, 100, 100),
                    "type": "page",
                    "text": "page text",
                }
            ]
        )
        canvas_obj = Canvas()
        # Test without idles
        mlp = safe_mainloop(2000)
        bboxes, indices = get_bboxes_and_indices(page.text_layer)
        canvas_obj.set_text(
            bboxes=bboxes,
            sorted_word_indices=indices,
            finished_callback=lambda: mlp.quit(),
        )
        mlp.run()

        assert canvas_obj.get_pixbuf_size() == {"width": 100, "height": 100}


def test_canvas_set_offset_pixbuf_none(mocker):
    "Test Canvas.set_offset when pixbuf_size is None"
    canvas_obj = Canvas()
    canvas_obj._pixbuf_size = None
    canvas_obj.set_offset(10, 10)
    # Should return early and not crash
    assert canvas_obj.get_offset().x == 0


def test_canvas_get_max_min_color_hsv(mocker):
    "Test color HSV getters"
    canvas_obj = Canvas()
    hsv = canvas_obj.get_max_color_hsv()
    assert "h" in hsv
    hsv = canvas_obj.get_min_color_hsv()
    assert "h" in hsv


def test_set_text_empty_list():
    "Test set_text with an empty list to cover lines 323-326"
    canvas = Canvas()
    canvas.clear_text = MagicMock()
    callback = MagicMock()
    canvas.set_text(bboxes=[], sorted_word_indices=[], finished_callback=callback)
    canvas.clear_text.assert_called_once()
    callback.assert_called_once()


def test_set_text_empty_generator():
    "Test set_text with an empty generator to cover lines 343-344"
    canvas = Canvas()

    def empty_gen():
        yield from []

    # Generators are truthy even when empty, so this bypasses 'if not bboxes'
    # but triggers StopIteration on next(itr)
    canvas.set_text(bboxes=empty_gen(), sorted_word_indices=[])
    # Should return early without crashing or scheduling idles
    assert (
        canvas.get_root_item() is None or canvas.get_root_item().get_n_children() == 0
    )


def test_set_text_empty_list_with_none_callback():
    "Test set_text with an empty list and finished_callback=None"
    canvas = Canvas()
    canvas.clear_text = MagicMock()
    # This should not raise 'NoneType' object is not callable
    canvas.set_text(bboxes=[], sorted_word_indices=[], finished_callback=None)
    canvas.clear_text.assert_called_once()


def test_bbox_button_press_callback(mocker):
    "Test Bbox button_press_callback"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="p",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    mock_edit = MagicMock()
    event = MagicMock()
    event.button = 1

    # We need a parent for the bbox that is NOT root to avoid _dragging check issue
    parent = canvas_obj.add_box(
        text="parent", bbox=Rectangle(x=0, y=0, width=100, height=100), parent=page
    )
    child = canvas_obj.add_box(
        text="c", bbox=Rectangle(x=0, y=0, width=10, height=10), parent=parent
    )
    button_press_callback(child, None, event, mock_edit)
    mock_edit.assert_called_once()


def test_bbox_walk_children(mocker):
    "Test Bbox.walk_children"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    line = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=20),
        type="line",
        parent=page,
    )
    word = canvas_obj.add_box(
        text="w", bbox=Rectangle(x=0, y=0, width=10, height=10), parent=line
    )

    visited = []

    def callback(bbox):
        visited.append(bbox)

    page.walk_children(callback)
    assert line in visited
    assert word in visited


def test_canvas_get_bbox_at_more(mocker):
    "Test Canvas.get_bbox_at"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    line = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=20),
        type="line",
        parent=page,
    )

    # get_bbox_at uses _find_bbox_at internally
    res = canvas_obj.get_bbox_at(Rectangle(x=10, y=10, width=1, height=1))
    assert res == line

    # Case where it returns a word -> we want the parent (line)
    word = canvas_obj.add_box(
        text="w", bbox=Rectangle(x=0, y=0, width=10, height=10), parent=line
    )
    res = canvas_obj.get_bbox_at(Rectangle(x=5, y=5, width=1, height=1))
    assert res == line


def test_bbox_to_hocr_more(mocker):
    "Test Bbox.to_hocr with extended properties"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="p",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        id="p1",
        parent=root,
    )
    page.baseline = [0.1, 5]
    page.confidence = 85
    page.textangle = 90

    hocr = page.to_hocr()
    assert "id='p1'" in hocr
    assert "baseline 0.1 5" in hocr
    assert "x_wconf 85" in hocr
    assert "textangle 90" in hocr


def test_bbox_stack_index_coverage(mocker):
    "Test get_stack_index_by_position coverage and robust binary search"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()

    # Create a page (not a line, so axis=1)
    page = canvas_obj.add_box(
        text="page",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )

    # No internal Rect/Text children in Cairo implementation.
    # children: [Bbox0, Bbox3, Bbox4] (indices 0, 1, 2)
    # y-centroids: b0=5, b3=45, b4=65
    canvas_obj.add_box(
        text="b0", bbox=Rectangle(x=0, y=0, width=10, height=10), parent=page
    )
    canvas_obj.add_box(
        text="b3", bbox=Rectangle(x=0, y=40, width=10, height=10), parent=page
    )
    canvas_obj.add_box(
        text="b4", bbox=Rectangle(x=0, y=60, width=10, height=10), parent=page
    )

    # 1. New box at y=35 (centroid y=40) -> between b0 (y=5) and b3 (y=45)
    new_bbox = MagicMock()
    new_bbox.get_centroid.return_value = (5, 40)

    idx = page.get_stack_index_by_position(new_bbox)
    assert idx == 1

    # 2. New box at y=70 (centroid y=75) -> after b4 (index 3)
    new_bbox.get_centroid.return_value = (5, 75)
    idx = page.get_stack_index_by_position(new_bbox)
    assert idx == 3

    # 3. New box at y=-5 (centroid y=0) -> before b0 (index 0)
    new_bbox.get_centroid.return_value = (5, 0)
    idx = page.get_stack_index_by_position(new_bbox)
    assert idx == 0


def test_tree_iter_next_word_stop_iteration(mocker):
    "Test TreeIter.next_word() state restoration on StopIteration (lines 1358-1361)"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()

    # Page -> Line (no words)
    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=20),
        type="line",
        parent=page,
    )

    ti = TreeIter(page)
    # ti starts at page.
    # ti.next_bbox() will be line. line.type != "word".
    # Subsequent ti.next_bbox() will raise StopIteration.
    # next_word should restore state and raise StopIteration.

    old_iter = ti._iter.copy()
    old_bbox = ti._bbox.copy()

    with pytest.raises(StopIteration):
        ti.next_word()

    assert ti._iter == old_iter
    assert ti._bbox == old_bbox


def test_tree_iter_previous_word_same_node(mocker):
    "Test TreeIter.previous_word() when previous_bbox returns same node (lines 1399-1401)"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="p",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        type="page",
        parent=root,
    )
    w1 = canvas_obj.add_box(
        text="w",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        type="word",
        parent=page,
    )

    ti = TreeIter(w1)

    # Force previous_bbox to return w1 (which is current_bbox[-1])
    # and ensure it's a word so loop terminates
    with patch.object(TreeIter, "previous_bbox", return_value=w1):
        with pytest.raises(StopIteration):
            ti.previous_word()


def test_list_iter_insert_before_position_warnings(mocker):
    "Test ListIter.insert_before_position() warnings (lines 1240-1247)"
    li = ListIter()
    mock_logger = mocker.patch("canvas.logger")

    # Line 1240: bbox is None
    li.insert_before_position(None, 0, 100)
    mock_logger.warning.assert_called_with(
        "Attempted to add undefined box to confidence list"
    )

    # Line 1244: i > len(self.list) - 1
    bbox = MagicMock()
    li.insert_before_position(bbox, 10, 100)
    mock_logger.warning.assert_called_with(
        "insert_before_position: position $i does not exist in index"
    )


def test_bbox_get_position_index_more(mocker):
    "Test Bbox.get_position_index() coverage (lines 966-978)"
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()

    # Create a page first to serve as the root Bbox for TreeIter
    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )

    # Case 1: parent.type == 'line' (sort_direction = 0)
    line = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=20),
        type="line",
        parent=page,
    )
    w1 = canvas_obj.add_box(
        text="w1", bbox=Rectangle(x=0, y=0, width=10, height=10), parent=line
    )
    w2 = canvas_obj.add_box(
        text="w2", bbox=Rectangle(x=20, y=0, width=10, height=10), parent=line
    )
    assert w1.get_position_index() == 0
    assert w2.get_position_index() == 1

    # Case 2: parent.type != 'line' (e.g. 'page', sort_direction = 1)
    l1 = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=20),
        type="line",
        parent=page,
    )
    l2 = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=30, width=100, height=20),
        type="line",
        parent=page,
    )
    # page already has 'line' from Case 1 at index 2 (indices 0,1 are Rect/Text)
    # page children (Bboxes): [line, l1, l2]
    assert l1.get_position_index() == 1
    assert l2.get_position_index() == 2

    # Case 3: Nested non-Bbox parent
    # page -> non-Bbox parent -> word. Since non-Bbox parent has no get_children(),
    # get_position_index raises IndexError when word not found in page's children.
    # We simulate by adding w3 directly to page then patching children
    w3 = canvas_obj.add_box(
        text="w3", bbox=Rectangle(x=0, y=0, width=10, height=10), parent=page
    )
    # Remove w3 from page's children list to simulate orphan
    page.children.remove(w3)
    with pytest.raises(IndexError):
        w3.get_position_index()

    # Case 4: IndexError (line 978) via mocking
    # We mock get_children to return a list NOT containing self
    with patch.object(Bbox, "get_children", return_value=[w1]):
        with pytest.raises(IndexError):
            w2.get_position_index()


def test_canvas_color_setters():
    "Test max_color and min_color setters update HSV properties (lines 224, 225, 248, 249)"
    canvas = Canvas()

    # max_color setter
    canvas.max_color = "blue"
    assert canvas.max_color == "blue"
    # blue is h=240 in rgb2hsv
    assert canvas.get_max_color_hsv()["h"] == pytest.approx(240)

    # min_color setter
    canvas.min_color = "green"
    assert canvas.min_color == "green"
    # green is h=120 in rgb2hsv
    assert canvas.get_min_color_hsv()["h"] == pytest.approx(120)


def test_color_functions_coverage():
    "Test color functions edge cases (lines 90, 119)"
    # Line 119: hsv2rgb with h >= 360
    c1 = hsv2rgb({"h": 360, "s": 1.0, "v": 1.0})
    c2 = hsv2rgb({"h": 0, "s": 1.0, "v": 1.0})
    assert_rgba_equal(c1, c2)

    # Line 90: rgb2hsv with h < 0.0
    # In Python % operator with positive divisor returns non-negative.
    # To hit line 90 we'd need hsv["h"] to be negative after * 60.
    # Since we can't easily trigger this with normal RGBA, we can check a value
    # that would be negative if not for % 6.
    # Actually, let's just test a color that uses the red case with green < blue.
    res = rgb2hsv(Gdk.RGBA(0.8, 0.1, 0.2))
    assert res["h"] >= 0.0
    assert res["h"] < 360.0


def test_canvas_index_none():
    "Test set_index_by_bbox and set_other_index with None bbox (lines 416, 425)"
    canvas = Canvas()

    # Line 416: set_index_by_bbox raises IndexError if bbox is None
    with pytest.raises(IndexError):
        canvas.set_index_by_bbox(None)

    # Line 425: set_other_index returns early if bbox is None
    # We can check that it doesn't try to access self._current_index or similar
    # by verifying no error is raised and state doesn't change
    canvas._current_index = "position"
    canvas.set_other_index(None)
    assert canvas._current_index == "position"


def test_canvas_add_box_with_transformation():
    "Test add_box with explicit transformation (line 495)"
    canvas = Canvas()
    canvas.confidence_index = ListIter()
    root = canvas.get_root_item()

    # Create page first
    page = canvas.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )

    # Provide explicit transformation
    trans = [10, 20, 30]
    bbox = canvas.add_box(
        text="test",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        parent=page,
        transformation=trans,
    )

    assert bbox.transformation == trans


def test_bbox_get_child_ordinal_not_found():
    "Test Bbox.get_child_ordinal() returns NOT_FOUND (line 974)"

    canvas = Canvas()
    canvas.confidence_index = ListIter()
    root = canvas.get_root_item()

    # Create page bbox to be parent of others
    page = canvas.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )

    bbox1 = canvas.add_box(
        text="b1",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        parent=page,
    )
    bbox2 = canvas.add_box(
        text="b2",
        bbox=Rectangle(x=20, y=0, width=10, height=10),
        parent=page,
    )

    # bbox1 is not a child of bbox2
    assert bbox2.get_child_ordinal(bbox1) == NOT_FOUND


def test_list_iter_set_index_by_bbox_not_found():
    "Test ListIter.set_index_by_bbox() when bbox is not found (lines 1183, 1184)"
    li = ListIter()
    bbox1 = MagicMock()
    bbox2 = MagicMock()

    # Add bbox1 to list
    li.add_box_to_index(bbox1, 50)

    # Try to find bbox2 which is NOT in the list
    res = li.set_index_by_bbox(bbox2, 50)
    assert res == EMPTY_LIST
    assert li.index == EMPTY_LIST


def test_tree_iter_first_last_word():
    "Test TreeIter.first_word() and last_word() branches (lines 1296, 1401)"
    canvas = Canvas()
    canvas.confidence_index = ListIter()
    root = canvas.get_root_item()

    # Create structure: Page -> Line -> Word
    page = canvas.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    canvas.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=20),
        type="line",
        parent=page,
    )

    # To hit 1296: return bbox (where bbox.type == "word")
    # We need a parent that is a Bbox for TreeIter init to work (get_child_ordinal)
    # The 'page' Bbox created earlier is a suitable parent.
    page_word = canvas.add_box(
        text="weird",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=page,
    )
    # Initialize TreeIter while it is still a "page" so it becomes the root of iteration
    ti_p = TreeIter(page_word)

    # Now change type to "word" so first_word() sees a word immediately
    page_word.type = "word"

    assert ti_p.first_word() == page_word

    # To hit 1401: while bbox is not None and bbox.type != "word"
    # Structure: Page -> Word1 -> Line (empty).
    # last_bbox() -> Line. Line != word.
    # previous_bbox() -> Word1. Word1 == word. Loop ends.

    # Page (is a "page" now)
    page.type = "page"
    w1 = canvas.add_box(
        text="w1",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        type="word",
        parent=page,
    )
    l1 = canvas.add_box(
        text="",
        bbox=Rectangle(x=0, y=20, width=100, height=10),
        type="line",
        parent=page,
    )

    ti_l = TreeIter(l1)
    assert ti_l.last_word() == w1


# Performance regression tests
def create_test_page_with_words(num_words, words_per_line=10):
    """Helper to create a test page with specified number of words"""
    boxes = []

    # Add page
    boxes.append(
        {
            "depth": 0,
            "bbox": [0, 0, 800, 1100],
            "type": "page",
            "text": "",
        }
    )

    # Add lines and words
    line_num = 0
    for i in range(0, num_words, words_per_line):
        # Add line
        y_pos = 50 + line_num * 30
        boxes.append(
            {
                "depth": 1,
                "bbox": [50, y_pos, 750, y_pos + 25],
                "type": "line",
                "text": "",
            }
        )

        # Add words in this line
        for j in range(min(words_per_line, num_words - i)):
            x_pos = 60 + j * 70
            boxes.append(
                {
                    "depth": 2,
                    "bbox": [x_pos, y_pos + 2, x_pos + 60, y_pos + 23],
                    "type": "word",
                    "text": f"word{i + j}",
                    "confidence": 50 + (i + j) % 50,  # Vary confidence
                }
            )

        line_num += 1

    return json.dumps(boxes)


@pytest.mark.slow
def test_canvas_no_stack_overflow(rose_pnm):
    """Test that large pages don't cause stack overflow.

    Before optimization, _boxed_text() was recursive and would hit
    Python's recursion limit (~1000) for large pages. This test ensures
    the iterative version can handle arbitrarily large pages.
    """
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=72,
            dir=dirname,
        )

        # Test with more than Python's default recursion limit
        num_words = 1500
        page.text_layer = create_test_page_with_words(num_words)
        # This should not raise RecursionError
        canvas = Canvas()
        mlp = safe_mainloop(10000)
        bboxes, indices = get_bboxes_and_indices(page.text_layer)
        canvas.set_text(
            bboxes=bboxes,
            sorted_word_indices=indices,
            finished_callback=lambda: mlp.quit(),
        )
        mlp.run()

        # Verify it actually loaded all words
        assert len(canvas.confidence_index.list) == num_words


def test_canvas_motion_no_dragging():
    "Test _motion returns False when not dragging (line 678)"
    canvas = Canvas()
    canvas._dragging = False
    assert canvas._motion(None, None) is False


def test_bbox_connect_new_signal(mocker):
    "Test Bbox.connect with a new signal name (line 233)"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    canvas.confidence_index = ListIter()
    root = canvas.get_root_item()
    page = canvas.add_box(
        text="p",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    page.connect("custom-signal", lambda: None)
    assert "custom-signal" in page._callbacks


def test_bbox_emit_callback(mocker):
    "Test Bbox.emit invokes callback (line 239)"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    canvas.confidence_index = ListIter()
    root = canvas.get_root_item()
    page = canvas.add_box(
        text="p",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    callback = MagicMock()
    page.connect("custom-signal", callback)
    page.emit("custom-signal", "arg1")
    callback.assert_called_once_with("arg1")


def test_delete_box_both_position_index_stop(mocker):
    "Test delete_box when position_index raises StopIteration on both next/previous (line 350)"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    canvas.confidence_index = ListIter()
    root = canvas.get_root_item()
    page = canvas.add_box(
        text="p",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    word = canvas.add_box(
        text="w",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        type="word",
        parent=page,
    )
    canvas.position_index = MagicMock()
    canvas.position_index.next_word.side_effect = StopIteration
    canvas.position_index.previous_word.side_effect = StopIteration
    word.delete_box()


def test_draw_scene_pixbuf_none(mocker):
    "Test _draw_scene returns early when pixbuf_size is None (lines 741-742)"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    canvas._pixbuf_size = None
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
    ctx = cairo.Context(surface)
    canvas._draw_scene(ctx)


def test_draw_bbox_full(mocker):
    "Test _draw_bbox and _draw_tree covering multiple branches (lines 744-827)"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    canvas._pixbuf_size = {"width": 100, "height": 100}
    canvas._zoom = 1.0
    canvas._offset = Gdk.Rectangle()
    canvas._offset.x = 0
    canvas._offset.y = 0
    rect = Gdk.Rectangle()
    rect.width = 200
    rect.height = 200
    canvas.get_allocation = MagicMock(return_value=rect)
    canvas.confidence_index = ListIter()
    root = canvas.get_root_item()

    page = canvas.add_box(
        text="page title",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
        textangle=45,
        confidence=100,
    )
    canvas.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=0, height=10),
        type="word",
        parent=page,
        confidence=100,
    )
    canvas.add_box(
        text="hello",
        bbox=Rectangle(x=0, y=0, width=50, height=10),
        type="word",
        parent=page,
        textangle=0,
        confidence=100,
    )
    canvas.add_box(
        text="world",
        bbox=Rectangle(x=0, y=0, width=50, height=10),
        type="word",
        parent=page,
        textangle=30,
        confidence=100,
    )

    pg_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 200)
    pg_ctx = cairo.Context(pg_surface)

    def make_layout(text):
        layout = PangoCairo.create_layout(pg_ctx)
        font_desc = Pango.FontDescription.from_string("Sans 10")
        layout.set_font_description(font_desc)
        layout.set_text(text, -1)
        return layout

    def patched_create_pango_layout(ctx, bbox):
        return make_layout(bbox.text)

    canvas._create_pango_layout = patched_create_pango_layout

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 200)
    ctx = cairo.Context(surface)
    canvas._draw_scene(ctx)
    canvas._draw_tree(ctx, None)


def test_hit_test_reference_error(mocker):
    "Test _hit_test raises ReferenceError when pixbuf or root is None (lines 940-941)"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    with pytest.raises(ReferenceError):
        canvas._hit_test(10, 10)
    canvas._pixbuf_size = {"width": 100, "height": 100}
    canvas._root_item = None
    with pytest.raises(ReferenceError):
        canvas._hit_test(10, 10)


def test_set_zoom_with_center_clamp(mocker):
    "Test _set_zoom_with_center clamps to MAX_ZOOM (line 1097)"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    rect = Gdk.Rectangle()
    rect.width = 200
    rect.height = 200
    canvas.get_allocation = MagicMock(return_value=rect)
    canvas._set_zoom_with_center(100, 0, 0)
    assert canvas.zoom == MAX_ZOOM


def test_draw_bbox_none_confidence(mocker):
    "Test _draw_bbox handles bbox with confidence=None (TypeError regression)"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    canvas._pixbuf_size = {"width": 100, "height": 100}
    canvas._zoom = 1.0
    canvas._offset = Gdk.Rectangle()
    canvas._offset.x = 0
    canvas._offset.y = 0
    rect = Gdk.Rectangle()
    rect.width = 200
    rect.height = 200
    canvas.get_allocation = MagicMock(return_value=rect)
    canvas.confidence_index = ListIter()
    root = canvas.get_root_item()

    page = canvas.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 200)
    ctx = cairo.Context(surface)
    canvas._draw_scene(ctx)


def test_hit_test_with_valid_state(mocker):
    "Test _hit_test with valid pixbuf_size and root_item (line 945)"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    canvas._pixbuf_size = {"width": 100, "height": 100}
    canvas._zoom = 1.0
    canvas._offset = Gdk.Rectangle()
    canvas._offset.x = 0
    canvas._offset.y = 0
    rect = Gdk.Rectangle()
    rect.width = 200
    rect.height = 200
    canvas.get_allocation = MagicMock(return_value=rect)
    canvas.confidence_index = ListIter()
    root = canvas.get_root_item()

    canvas.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )

    result = canvas._hit_test(50, 50)
    assert result is not None


def test_hit_test_nonzero_offset(mocker):
    "Test _hit_test with non-zero offset matches forward transform"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    canvas._pixbuf_size = {"width": 1000, "height": 1000}
    canvas._zoom = 2.0
    canvas._offset = Gdk.Rectangle()
    canvas._offset.x = 50
    canvas._offset.y = 30
    rect = Gdk.Rectangle()
    rect.width = 200
    rect.height = 200
    canvas.get_allocation = MagicMock(return_value=rect)
    canvas.confidence_index = ListIter()
    root = canvas.get_root_item()

    page = canvas.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=1000, height=1000),
        type="page",
        parent=root,
    )

    line = canvas.add_box(
        text="",
        bbox=Rectangle(x=30, y=30, width=10, height=10),
        type="line",
        parent=page,
    )

    # Forward: wx = (ix + ox) * zoom
    # For image pixel (35, 35): wx = (35 + 50) * 2 = 170, wy = (35 + 30) * 2 = 130
    # hit_test should recover (35, 35) and find the line
    result = canvas._hit_test(170, 130)
    assert result is not None
    assert result.type == "line"


def test_button_press_callback_edge_cases():
    "Test button_press_callback with button != 1 and no canvas"
    bbox = MagicMock()
    bbox.canvas = None

    event = MagicMock()
    event.button = 2
    callback = MagicMock()
    button_press_callback(bbox, None, event, callback)
    callback.assert_not_called()
    bbox.emit.assert_not_called()

    event = MagicMock()
    event.button = 1
    callback = MagicMock()
    button_press_callback(bbox, None, event, callback)
    callback.assert_called_once_with(bbox, None)
    bbox.emit.assert_called_once_with("clicked")


def test_bbox_connect_duplicate_signal():
    "Test Bbox.connect when signal already registered"
    bbox = Bbox()
    cb = MagicMock()
    bbox.connect("sig", cb)
    bbox.connect("sig", cb)
    assert len(bbox._callbacks["sig"]) == 2


def test_bbox_get_position_index_non_bbox_parent(mocker):
    "Test get_position_index traverses non-Bbox parents"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()

    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    child = canvas_obj.add_box(
        text="c1",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        parent=page,
    )

    class NonBboxParent:
        parent = page

    child.parent = NonBboxParent()
    idx = child.get_position_index()
    assert idx == 0


def test_bbox_walk_children_none_callback(mocker):
    "Test walk_children with None callback"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    canvas_obj.add_box(
        text="child",
        bbox=Rectangle(x=0, y=0, width=50, height=50),
        type="word",
        parent=page,
    )
    page.walk_children(None)


def test_bbox_update_box_no_canvas(mocker):
    "Test update_box when canvas is None (covers 302->305, 327->exit)"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="page",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    word = canvas_obj.add_box(
        text="word",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        type="word",
        parent=page,
    )
    word.canvas = None
    word.update_box("new", Rectangle(x=5, y=5, width=15, height=15))
    assert word.text == "new"


def test_bbox_update_box_page_type_skips_bbox(mocker):
    "Test update_box with type 'page' skips bbox update (covers 307->310)"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    canvas_obj.position_index = MagicMock()
    root = canvas_obj.get_root_item()
    container = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=200, height=200),
        type="line",
        parent=root,
    )
    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=container,
    )
    page.update_box("title", Rectangle(x=10, y=10, width=80, height=80))
    assert page.text == "title"
    assert page.bbox.x == 0


def test_bbox_update_box_indices_out_of_range(mocker):
    "Test update_box when indices are out of parent_children bounds"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    word = canvas_obj.add_box(
        text="old",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        type="word",
        parent=page,
    )
    with patch.object(Bbox, "get_position_index", side_effect=[0, 99]):
        word.update_box("new", Rectangle(x=5, y=5, width=15, height=15))
    assert word.text == "new"


def test_bbox_delete_box_no_canvas():
    "Test delete_box with bbox that has no canvas"
    bbox = Bbox(
        text="test",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
    )
    bbox.delete_box()


def test_bbox_delete_box_parent_none_or_not_found(mocker):
    "Test delete_box with parent None or self not found in children"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    word = canvas_obj.add_box(
        text="w",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        type="word",
        parent=page,
    )
    word.parent = None
    word.delete_box()


def test_bbox_delete_box_self_not_in_children(mocker):
    "Test delete_box when self is not found in parent_children"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()
    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    word = canvas_obj.add_box(
        text="w",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        type="word",
        parent=page,
    )
    page.children.remove(word)
    word.delete_box()


def test_bbox_to_hocr_falsy_bbox_or_type():
    "Test to_hocr returns empty string when bbox or type is falsy"
    bbox_no_bbox = Bbox(text="test", type="word")
    assert bbox_no_bbox.to_hocr() == ""

    bbox_no_type = Bbox(
        text="test",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        type=None,
    )
    assert bbox_no_type.to_hocr() == ""


def test_get_color_for_confidence_lookup_exists(mocker):
    "Test get_color_for_confidence when lookup table already built"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas_obj = Canvas()
    canvas_obj._color_lookup_table = ["#ff0000"]
    result = canvas_obj.get_color_for_confidence(75)
    assert result == "#ff0000"


def test_canvas_set_text_finished_with_rebuild_edge(mocker, rose_pnm):
    "Test set_text finished_with_rebuild with missing bbox and no callback"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=72,
            dir=dirname,
        )
        page.text_layer = json.dumps(
            [
                {
                    "depth": 0,
                    "bbox": (0, 0, 100, 100),
                    "type": "page",
                    "text": "",
                },
                {
                    "depth": 1,
                    "bbox": (0, 0, 50, 20),
                    "type": "word",
                    "text": "",
                    "confidence": 90,
                },
                {
                    "depth": 1,
                    "bbox": (10, 0, 50, 20),
                    "type": "word",
                    "text": "hello",
                    "confidence": 80,
                },
            ]
        )
        canvas_obj = Canvas()
        mlp = safe_mainloop(2000)
        bboxes, indices = get_bboxes_and_indices(page.text_layer)
        callback_mock = MagicMock()
        canvas_obj.set_text(
            bboxes=bboxes,
            sorted_word_indices=indices,
            finished_callback=callback_mock,
        )
        GLib.timeout_add(500, mlp.quit)
        mlp.run()
        callback_mock.assert_called_once()


def test_canvas_on_draw(mocker):
    "Test _on_draw handler"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    canvas._pixbuf_size = {"width": 100, "height": 100}
    canvas._zoom = 1.0
    canvas._offset = Gdk.Rectangle()
    canvas._offset.x = 0
    canvas._offset.y = 0
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
    ctx = cairo.Context(surface)
    canvas._on_draw(None, ctx)


def test_draw_bbox_more_branches(mocker):
    "Test _draw_bbox with layout cached, layout None, zero-width, no rotation"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    canvas._pixbuf_size = {"width": 100, "height": 100}
    canvas._zoom = 1.0
    canvas._offset = Gdk.Rectangle()
    canvas._offset.x = 0
    canvas._offset.y = 0
    rect = Gdk.Rectangle()
    rect.width = 200
    rect.height = 200
    canvas.get_allocation = MagicMock(return_value=rect)
    canvas.confidence_index = ListIter()
    root = canvas.get_root_item()

    page = canvas.add_box(
        text="title",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
        textangle=0,
        transformation=[0, 0, 0],
        confidence=100,
    )

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 200)
    ctx = cairo.Context(surface)

    def make_layout(ctx2, bbox):
        layout = PangoCairo.create_layout(ctx2)
        font_desc = Pango.FontDescription.from_string("Sans 10")
        layout.set_font_description(font_desc)
        layout.set_text(bbox.text, -1)
        return layout

    page._pango_layout = make_layout(ctx, page)
    canvas._draw_scene(ctx)

    word = canvas.add_box(
        text="zero",
        bbox=Rectangle(x=50, y=50, width=50, height=10),
        type="word",
        parent=page,
        textangle=0,
        transformation=[0, 0, 0],
        confidence=100,
    )
    canvas._create_pango_layout = MagicMock(return_value=None)
    canvas._draw_scene(ctx)

    mock_layout = MagicMock()
    ink = MagicMock()
    ink.width = 0
    ink.height = 10
    mock_layout.get_pixel_extents.return_value = (ink, MagicMock())
    word._pango_layout = mock_layout
    del canvas._create_pango_layout
    canvas._draw_scene(ctx)

    word2 = canvas.add_box(
        text="new",
        bbox=Rectangle(x=30, y=30, width=40, height=10),
        type="word",
        parent=page,
        textangle=0,
        transformation=[0, 0, 0],
        confidence=100,
    )
    canvas._draw_scene(ctx)

    canvas._draw_tree(ctx, None)


def test_find_bbox_at_edge_cases(mocker):
    "Test _find_bbox_at with item=None and child with bbox=None"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas_obj = Canvas()
    result = canvas_obj._find_bbox_at(None, 10, 10)
    assert result is None

    root = canvas_obj.get_root_item()
    child = Bbox(text="test")
    root.children.append(child)
    result = canvas_obj._find_bbox_at(root, 10, 10)
    assert result is None


def test_boxed_text_no_callback(mocker):
    "Test _boxed_text when finished_callback is falsy"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    canvas._pixbuf_size = {"width": 100, "height": 100}
    canvas._zoom = 1.0
    canvas._offset = Gdk.Rectangle()
    canvas._offset.x = 0
    canvas._offset.y = 0
    canvas.confidence_index = ListIter()
    canvas.position_index = MagicMock()
    parent_mock = MagicMock()
    options = {
        "iter": iter([]),
        "idx": 0,
        "box": {"depth": 0, "bbox": (0, 0, 10, 10), "text": "t"},
        "transformations": [[0, 0, 0]],
        "parents": [parent_mock],
        "edit_callback": None,
        "bbox_map": {},
        "skip_confidence_index": True,
        "finished_callback": None,
    }
    result = canvas._boxed_text(options)
    assert result == GLib.SOURCE_REMOVE


def test_button_pressed_released_more(mocker):
    "Test _button_pressed and _button_released edge cases"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    canvas._pixbuf_size = {"width": 100, "height": 100}
    canvas._zoom = 1.0
    canvas._offset = Gdk.Rectangle()
    canvas._offset.x = 0
    canvas._offset.y = 0
    rect = Gdk.Rectangle()
    rect.width = 200
    rect.height = 200
    canvas.get_allocation = MagicMock(return_value=rect)
    canvas.get_window = MagicMock(return_value=MagicMock())
    canvas.confidence_index = ListIter()
    root = canvas.get_root_item()
    canvas.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
        edit_callback=MagicMock(),
    )

    event = MagicMock()
    event.button = 1
    event.x = 50
    event.y = 50
    canvas._button_pressed(None, event)

    event = MagicMock()
    event.button = 3
    canvas._button_pressed(None, event)

    canvas._pixbuf_size = None
    event = MagicMock()
    event.button = 1
    canvas._button_pressed(None, event)


def test_list_iter_get_previous_bbox_at_zero():
    "Test get_previous_bbox when index is already 0"
    li = ListIter()
    bbox = MagicMock()
    li.add_box_to_index(bbox, 90)
    li.get_first_bbox()
    result = li.get_previous_bbox()
    assert result == bbox
    assert li.index == 0


def test_tree_iter_non_bbox_children(mocker):
    "Test TreeIter with non-Bbox children and siblings"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas_obj = Canvas()
    canvas_obj.confidence_index = ListIter()
    root = canvas_obj.get_root_item()

    page = canvas_obj.add_box(
        text="",
        bbox=Rectangle(x=0, y=0, width=100, height=100),
        type="page",
        parent=root,
    )
    canvas_obj.add_box(
        text="w1",
        bbox=Rectangle(x=0, y=0, width=10, height=10),
        type="word",
        parent=page,
    )
    canvas_obj.add_box(
        text="w2",
        bbox=Rectangle(x=20, y=0, width=10, height=10),
        type="word",
        parent=page,
    )

    non_bbox = MagicMock()
    page.children.insert(0, non_bbox)
    page.children.append(MagicMock())

    ti = TreeIter(page)
    ti.next_bbox()
    ti.next_bbox()
