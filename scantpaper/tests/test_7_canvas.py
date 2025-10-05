"Test Canvas class"

from dataclasses import dataclass
import tempfile
import pytest
import gi
from page import Page
from canvas import Canvas, Bbox, Rectangle
from canvas import HOCR_HEADER as HOCR_OUT_HEADER
from conftest import HOCR_HEADER

gi.require_version("GooCanvas", "2.0")
from gi.repository import (  # pylint: disable=wrong-import-position,no-name-in-module
    GooCanvas,
)


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
    mock_display.return_value.get_default_seat.return_value.get_pointer.return_value.get_position.side_effect = [  # pylint: disable=line-too-long
        (None, 10, 10),
        (None, 20, 20),
    ]
    canvas = Canvas()
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
