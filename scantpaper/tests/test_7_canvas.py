"Test Canvas class"

import os
import subprocess
import tempfile
import gi
from page import Page
from canvas import Canvas, Bbox, Rectangle
from canvas import HOCR_HEADER as HOCR_OUT_HEADER
from conftest import HOCR_HEADER

gi.require_version("GooCanvas", "2.0")
gi.require_version("Gdk", "3.0")
from gi.repository import (  # pylint: disable=wrong-import-position,no-name-in-module
    Gdk,
    GooCanvas,
)


def test_basic():
    "Basic tests"

    # Create test image
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    page = Page(
        filename="test.pnm",
        format="Portable anymap",
        resolution=72,
        dir=tempfile.mkdtemp(),
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
    canvas.set_text(page, "text_layer", None, False)

    bbox = canvas.get_first_bbox()
    assert bbox.text == "The—", "get_first_bbox"
    assert canvas.set_index_by_bbox(bbox) == 0, "set_index_by_bbox 1"
    bbox = canvas.get_next_bbox()
    assert bbox.text == "fox", "get_next_bbox"
    assert canvas.set_index_by_bbox(bbox) == 1, "set_index_by_bbox 2"
    assert canvas.get_previous_bbox().text == "The—", "get_previous_text"
    bbox = canvas.get_last_bbox()
    assert bbox.text == "brown", "get_last_text"
    assert canvas.set_index_by_bbox(bbox) == 3, "set_index_by_bbox 3"

    bbox.delete_box()
    assert canvas.get_last_bbox().text == "quick", "get_last_bbox after deletion"

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
    assert canvas.get_previous_bbox() is None, "before get_first_bbox position"
    bbox = canvas.get_next_bbox()
    assert bbox.text == "quick", "get_next_bbox position"
    bbox = canvas.get_previous_bbox()
    assert bbox.text == "No", "get_previous_bbox position"
    bbox = canvas.get_last_bbox()
    assert bbox.text == "foo", "get_last_bbox position"
    assert canvas.get_next_bbox() is None, "after get_last_bbox position"

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
    canvas.get_last_bbox().update_box("No", Rectangle(x=2, y=15, width=75, height=32))
    assert (
        canvas.get_last_bbox().text == "No"
    ), "don't sort if confidence hasn't changed"

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

    os.remove("test.pnm")


def test_hocr():
    "Tests hocr export"

    # Create test image
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    page = Page(
        filename="test.pnm",
        format="Portable anymap",
        resolution=72,
        dir=tempfile.mkdtemp(),
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
    canvas.set_text(page, "text_layer", None, False)
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

    assert canvas.hocr() == expected  #  'updated hocr with extended hOCR properties'

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
    assert canvas.get_last_bbox() is None, "get_last_bbox() returns undef if no boxes"

    #########################

    os.remove("test.pnm")
