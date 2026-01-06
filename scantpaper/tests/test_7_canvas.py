"Test Canvas class"

from dataclasses import dataclass
from unittest.mock import MagicMock, patch
import tempfile
import pytest
import gi
from page import Page
from canvas import rgb2hsv, hsv2rgb, Canvas, Bbox, Rectangle, ListIter
from canvas import HOCR_HEADER as HOCR_OUT_HEADER
from conftest import HOCR_HEADER

gi.require_version("GooCanvas", "2.0")
gi.require_version("Gdk", "3.0")
from gi.repository import (  # pylint: disable=wrong-import-position,no-name-in-module
    Gdk,
    GooCanvas,
    GLib,
)


def assert_rgba_equal(c1, c2):
    "Assert two Gdk.RGBA colors are equal"
    assert c1.red == pytest.approx(c2.red)
    assert c1.green == pytest.approx(c2.green)
    assert c1.blue == pytest.approx(c2.blue)


def test_color_functions():
    "Test standalone color conversion functions"
    # rgb2hsv
    assert rgb2hsv(Gdk.RGBA(0, 0, 0)) == {"h": 0, "s": 0, "v": 0}
    assert rgb2hsv(Gdk.RGBA(0.5, 0.5, 0.5)) == {"h": 0, "s": 0, "v": 0.5}

    # hsv2rgb
    assert_rgba_equal(hsv2rgb({"h": 0, "s": 0, "v": 1.0}), Gdk.RGBA(1.0, 1.0, 1.0))


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
            filename=rose_pnm.name,
            format="Portable anymap",
            resolution=72,
            dir=dirname,
        )
        page.import_hocr(
            HOCR_HEADER
            + """ <body>
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
"""
        )

        canvas = Canvas()
        canvas.sort_by_confidence()
        canvas.set_text(page=page, layer="text_layer", idle=False)

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

        #########################

        assert canvas.get_bounds() == (0, 0, 70, 46), "get_bounds"
        assert canvas.get_scale() == 1, "get_scale"
        canvas._set_zoom_with_center(2, 35, 26)
        assert canvas.get_bounds() == (0, 0, 70, 46), "get_bounds after zoom"
        assert canvas.convert_from_pixels(0, 0) == (0, 0), "convert_from_pixels"
        width, height = page.get_size()
        canvas.set_bounds(-10, -10, width + 10, height + 10)
        assert canvas.get_bounds() == (-10, -10, 80, 56), "get_bounds after set"
        assert canvas.convert_from_pixels(0, 0) == (-10, -10), "convert_from_pixels2"


def test_canvas_basics2(rose_pnm):
    "Basic tests"
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm.name,
            format="Portable anymap",
            resolution=72,
            dir=dirname,
        )
        page.import_hocr(
            HOCR_HEADER
            + """ <body>
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
"""
        )

        canvas = Canvas()
        canvas.sort_by_confidence()
        canvas.set_text(page=page, layer="text_layer", idle=False)

        group = (
            canvas.get_root_item()
            .get_child(0)
            .get_children()[0]
            .get_children()[0]
            .get_children()[0]
        )
        group.update_box("No", Rectangle(x=2, y=15, width=74, height=32))

        canvas.add_box(text="foo", bbox=Rectangle(x=355, y=15, width=74, height=32))

        expected = (
            HOCR_OUT_HEADER
            + """ <body>
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
        )

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

        expected = (
            HOCR_OUT_HEADER
            + """ <body>
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
        )

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
        assert group.confidence2color() == "#7fff3fff3fff", "mid way"
        group.confidence = 40
        assert group.confidence2color() == "red", "< min"

        #########################

        group.update_box("<em>No</em>", Rectangle(x=2, y=15, width=74, height=32))

        expected = (
            HOCR_OUT_HEADER
            + """ <body>
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
        )

        assert canvas.hocr() == expected, "updated hocr with HTML-escape characters"


def test_canvas_clear_text(mocker):  # pylint: disable=unused-argument
    "Test clearing text from canvas"
    canvas_obj = Canvas()
    canvas_obj._pixbuf_size = {  # pylint: disable=protected-access
        "width": 100,
        "height": 100,
    }
    canvas_obj.set_root_item = MagicMock()

    with patch("canvas.GooCanvas.CanvasGroup") as mock_group:
        canvas_obj.clear_text()
        assert canvas_obj.get_pixbuf_size() is None
        mock_group.assert_called()
        canvas_obj.set_root_item.assert_called()


def test_hocr(rose_pnm):
    "Tests hocr export"
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm.name,
            format="Portable anymap",
            resolution=72,
            dir=dirname,
        )

        page.import_hocr(
            HOCR_HEADER
            + """ <body>
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
"""
        )

        canvas = Canvas()
        canvas.set_text(page=page, layer="text_layer", idle=False)
        canvas.sort_by_confidence()

        expected = (
            HOCR_OUT_HEADER
            + """ <body>
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
        )

        assert (
            canvas.hocr() == expected
        )  #  'updated hocr with extended hOCR properties'

        #########################

        group = canvas.get_root_item()

        # get page 'page_1'
        group = group.get_child(0)

        # get column/carea 'block_1'
        group = group.get_child(1)

        # get line 'line_1_2'
        group = group.get_child(2)

        # get word 'word_1_3'
        bbox = group.get_child(1)

        assert isinstance(bbox, Bbox)
        assert bbox.textangle == 0, "word_1_3's textangle is 0"
        assert bbox.transformation[0] == 90, "word_1_3's (inherited) rotation is 90"
        textwidget = bbox.get_text_widget()
        assert isinstance(textwidget, GooCanvas.CanvasText)

        transform = textwidget.get_simple_transform()

        assert (
            transform[-1] == 270
        ), "word_1_3's text widget rotation matches the 90° rotation"

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
            filename=rose_pnm.name,
            format="Portable anymap",
            resolution=72,
            dir=dirname,
        )
        page.import_hocr(
            HOCR_HEADER
            + """<body>
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
 """
        )
        canvas = Canvas()
        canvas.set_text(page=page, layer="text_layer", idle=False)

        # Get the bbox for the word 'fox'
        bbox = canvas.get_first_bbox()
        assert bbox.text == "fox"

        # Get the rectangle and text widgets
        rect_widget = bbox.get_box_widget()
        assert isinstance(
            rect_widget, GooCanvas.CanvasRect
        ), "Could not find rectangle widget in Bbox"
        text_widget = bbox.get_text_widget()

        # Get their bounds in the canvas coordinate system
        rect_bounds = rect_widget.get_bounds()
        text_bounds = text_widget.get_bounds()

        # The text should be inside the rectangle.
        # Allow for a small tolerance due to font rendering.
        tolerance = 1.0
        assert text_bounds.x1 >= rect_bounds.x1 - tolerance
        assert text_bounds.y1 >= rect_bounds.y1 - tolerance
        assert text_bounds.x2 <= rect_bounds.x2 + tolerance
        assert text_bounds.y2 <= rect_bounds.y2 + tolerance


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
        x: int  # pylint: disable=invalid-name
        y: int  # pylint: disable=invalid-name

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
    canvas._pixbuf_size = {  # pylint: disable=protected-access
        "width": 100,
        "height": 100,
    }

    event = MockEvent(button=2, x=10, y=10)
    canvas._button_pressed(canvas, event)  # pylint: disable=protected-access
    event.x = 20
    event.y = 20
    try:
        canvas._motion(canvas, event)  # pylint: disable=protected-access
    except TypeError:
        pytest.fail("Dragging a text layer should not raise a TypeError")


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


def test_canvas_set_text_idles(mocker):
    "Test set_text with existing idles"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    canvas._old_idles = {"dummy": 1}
    mocker.patch("gi.repository.GLib.Source.remove")
    page = mocker.Mock()
    page.get_size.return_value = (100, 100)
    page.text_layer = "[]"
    canvas.set_text(page=page, layer="text_layer", idle=False)
    assert GLib.Source.remove.called


def test_canvas_hocr_empty(mocker):
    "Test Canvas.hocr when empty"
    mocker.patch("gi.repository.Gdk.Display.get_default")
    canvas = Canvas()
    assert canvas.hocr() == ""


def test_canvas_set_offset_clamping(mocker):  # pylint: disable=unused-argument
    "Test set_offset clamping logic"
    canvas_obj = Canvas()
    canvas_obj.scroll_to = MagicMock()

    canvas_obj._pixbuf_size = None  # pylint: disable=protected-access
    canvas_obj.set_offset(10, 10)
    assert canvas_obj.offset.x == 0 and canvas_obj.offset.y == 0

    canvas_obj._pixbuf_size = {  # pylint: disable=protected-access
        "width": 100,
        "height": 100,
    }

    rect = Gdk.Rectangle()
    rect.width = 200
    rect.height = 200
    canvas_obj.get_allocation = MagicMock(return_value=rect)

    canvas_obj._to_image_distance = MagicMock(  # pylint: disable=protected-access
        return_value=(200, 200)
    )
    canvas_obj.get_scale_factor = MagicMock(return_value=1)

    canvas_obj.set_offset(0, 0)
    assert canvas_obj.offset.x == 50
    assert canvas_obj.offset.y == 50

    canvas_obj._pixbuf_size = {  # pylint: disable=protected-access
        "width": 300,
        "height": 300,
    }
    canvas_obj._to_image_distance = MagicMock(  # pylint: disable=protected-access
        return_value=(200, 200)
    )

    canvas_obj.set_offset(10, 10)
    assert canvas_obj.offset.x == 0
    assert canvas_obj.offset.y == 0

    canvas_obj.set_offset(-150, -150)
    assert canvas_obj.offset.x == -100
    assert canvas_obj.offset.y == -100


def test_canvas_scroll(mocker):  # pylint: disable=unused-argument
    "Test scroll event zooming"
    canvas_obj = Canvas()
    canvas_obj.set_scale(1.0)

    canvas_obj.get_scale_factor = MagicMock(return_value=1)
    canvas_obj.convert_from_pixels = MagicMock(return_value=(50, 50))

    event = MagicMock()
    event.x = 50
    event.y = 50
    event.direction = Gdk.ScrollDirection.UP

    canvas_obj._pixbuf_size = {  # pylint: disable=protected-access
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
        canvas_obj.scroll_to = MagicMock()

        canvas_obj._scroll(canvas_obj, event)  # pylint: disable=protected-access
        assert canvas_obj.get_scale() == 2.0
        mock_set_offset.assert_called()

    event.direction = Gdk.ScrollDirection.DOWN
    canvas_obj._scroll(canvas_obj, event)  # pylint: disable=protected-access
    assert canvas_obj.get_scale() == 1.0


def test_canvas_get_bbox_at(mocker):  # pylint: disable=unused-argument
    "Test get_bbox_at"
    canvas_obj = Canvas()

    bbox_rect = Rectangle(x=10, y=10, width=20, height=20)

    mock_item = MagicMock()
    mock_item.type = "line"
    canvas_obj.get_item_at = MagicMock(return_value=mock_item)

    result = canvas_obj.get_bbox_at(bbox_rect)
    assert result == mock_item

    mock_word = MagicMock()
    mock_word.type = "word"
    mock_parent = MagicMock()
    mock_parent.type = "line"
    mock_word.get_parent.return_value = mock_parent
    canvas_obj.get_item_at = MagicMock(return_value=mock_word)

    result = canvas_obj.get_bbox_at(bbox_rect)
    assert result == mock_parent

    mock_orphan = MagicMock()
    mock_orphan.type = "word"
    mock_orphan.get_parent.return_value = None
    canvas_obj.get_item_at = MagicMock(return_value=mock_orphan)
    with pytest.raises(ReferenceError):
        canvas_obj.get_bbox_at(bbox_rect)

    canvas_obj.get_item_at = MagicMock(return_value=None)
    with pytest.raises(ReferenceError):
        canvas_obj.get_bbox_at(bbox_rect)


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


def test_bbox_methods_via_canvas(mocker):  # pylint: disable=unused-argument
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
