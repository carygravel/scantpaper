"Tests for Page class"

import os
import subprocess
import tempfile
from PIL import Image
from page import Page, _prepare_scale, VERSION
from gi.repository import GdkPixbuf
import pytest


def test_1():
    "Tests for Page class"
    with pytest.raises(ValueError):
        page = Page(
            dir=tempfile.mkdtemp(),
        )
    with pytest.raises(FileNotFoundError):
        page = Page(
            filename="test.pnm",
            format="PBM",
            dir=tempfile.mkdtemp(),
        )

    # Create test image
    subprocess.run(["convert", "-size", "210x297", "xc:white", "test.pnm"], check=True)
    image_object = Image.new("RGB", (210, 297))

    #########################

    paper_sizes = {
        "A4": {
            "x": 210,
            "y": 297,
            "l": 0,
            "t": 0,
        },
        "US Letter": {
            "x": 216,
            "y": 279,
            "l": 0,
            "t": 0,
        },
        "US Legal": {
            "x": 216,
            "y": 356,
            "l": 0,
            "t": 0,
        },
    }

    page = Page(
        image_object=image_object,
        dir=tempfile.mkdtemp(),
    )
    assert page.matching_paper_sizes(paper_sizes) == {"A4": 25.4}, "from image object"

    page = Page(
        filename="test.pnm",
        dir=tempfile.mkdtemp(),
    )
    assert page.matching_paper_sizes(paper_sizes) == {"A4": 25.4}, "basic portrait"
    page = Page(
        filename="test.pnm",
        dir=tempfile.mkdtemp(),
    )
    assert page.matching_paper_sizes(paper_sizes) == {"A4": 25.4}, "basic landscape"

    #########################

    assert page.get_resolution(paper_sizes) == (
        25.4,
        25.4,
        "PixelsPerInch",
    ), "resolution"

    subprocess.run(
        [
            "convert",
            "-units",
            "PixelsPerInch",
            "-density",
            "300",
            "xc:white",
            "test.jpg",
        ],
        check=True,
    )
    page = Page(
        filename="test.jpg",
        dir=tempfile.mkdtemp(),
    )
    assert page.get_resolution(paper_sizes) == (300.0, 300.0, "PixelsPerInch"), "inches"

    subprocess.run(
        [
            "convert",
            "-units",
            "PixelsPerCentimeter",
            "-density",
            "118",
            "xc:white",
            "test.jpg",
        ],
        check=True,
    )
    page = Page(
        filename="test.jpg",
        dir=tempfile.mkdtemp(),
    )
    assert page.get_resolution(paper_sizes) == (
        299.72,
        299.72,
        "PixelsPerCentimeter",
    ), "centimetres"

    subprocess.run(
        ["convert", "-units", "Undefined", "-density", "300", "xc:white", "test.jpg"],
        check=True,
    )
    page = Page(
        filename="test.jpg",
        dir=tempfile.mkdtemp(),
    )
    assert page.get_resolution(paper_sizes) == (
        300.0,
        300.0,
        "PixelsPerInch",
    ), "undefined"
    os.remove("test.jpg")

    #########################

    assert _prepare_scale(1000, 100, 1, 100, 100) == (100, 10.0), "scale x, ratio 1"
    assert _prepare_scale(100, 1000, 1, 100, 100) == (10, 100.0), "scale y, ratio 1"
    assert _prepare_scale(1000, 100, 2, 100, 100) == (100, 20.0), "scale x, ratio 2"
    assert _prepare_scale(100, 1000, 2, 100, 100) == (5, 100.0), "scale y, ratio 2"
    assert _prepare_scale(0, 1000, 2, 100, 100) == (None, None), "invalid"

    #########################

    assert page.export_djvu_txt() is None, "export_djvu_txt() without bboxes"
    assert page.export_text() is None, "export_text() without bboxes"
    assert page.export_djvu_ann() is None, "export_djvu_ann() without bboxes"


def test_2(clean_up_files):
    "Tests for Page class"

    subprocess.run(["convert", "-size", "210x297", "xc:white", "test.pnm"], check=True)

    with pytest.raises(ValueError):
        page = Page(
            filename="test.pnm",
            dir=tempfile.mkdtemp(),
            size=[105, 148, "elephants"],
        )
        page.get_resolution()

    page = Page(
        filename="test.pnm",
        dir=tempfile.mkdtemp(),
        size=[105, 148, "pts"],
    )
    assert page.get_resolution() == (
        144.0,
        144.48648648648648,
        "PixelsPerInch",
    ), "from pdfinfo paper size"

    page = Page(
        filename="test.pnm",
        dir=tempfile.mkdtemp(),
    )
    assert page.get_resolution() == (72, 72, "PixelsPerInch"), "default to 72"

    #########################

    new_page = page.clone()
    assert new_page.image_object == page.image_object, "clone"

    #########################

    hocr = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='gscan2pdf {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' id='page_1' title='bbox 0 0 422 61'>
   <div class='ocr_carea' id='block_1_1' title='bbox 1 14 420 59'>
    <span class='ocr_line' id='line_1_1' title='bbox 1 14 420 59; baseline -0.003 -17'>
     <span class='ocr_word' id='word_1_1' title='bbox 1 14 77 48; textangle 90; x_wconf -3'>The</span>
     <span class='ocr_word' id='word_1_2' title='bbox 92 14 202 59; x_wconf -3'>quick</span>
     <span class='ocr_word' id='word_1_3' title='bbox 214 14 341 48; x_wconf -3'>brown</span>
     <span class='ocr_word' id='word_1_4' title='bbox 355 14 420 48; x_wconf -4'>fox</span>
    </span>
   </div>
  </div>
 </body>
</html>
"""
    page.import_hocr(hocr)
    assert (
        page.text_layer
        == '[{"bbox": [0, 0, 422, 61], "type": "page", "id": "page_1", "depth": 0}, '
        '{"bbox": [1, 14, 420, 59], "type": "column", "id": "block_1_1", "depth": 1}, '
        '{"bbox": [1, 14, 420, 59], "baseline": [-0.003, -17], "type": "line", "id": "line_1_1", '
        '"depth": 2}, {"bbox": [1, 14, 77, 48], "textangle": 90, "confidence": -3, "type": "word", '
        '"id": "word_1_1", "text": "The", "depth": 3}, '
        '{"bbox": [92, 14, 202, 59], "confidence": -3, "type": "word", "id": "word_1_2", '
        '"text": "quick", "depth": 3}, '
        '{"bbox": [214, 14, 341, 48], "confidence": -3, "type": "word", "id": "word_1_3", '
        '"text": "brown", "depth": 3}, '
        '{"bbox": [355, 14, 420, 48], "confidence": -4, "type": "word", "id": "word_1_4", '
        '"text": "fox", "depth": 3}]'
    ), "import_hocr()"
    assert page.export_hocr() == hocr, "export_hocr()"

    #########################

    djvu_txt = """(page 0 0 422 61 "The quick brown fox")
"""
    page.import_djvu_txt(djvu_txt)
    assert (
        page.text_layer
        == '[{"depth": 0, "type": "page", "bbox": [0, 0, 422, 61], "text": "The quick brown fox"}]'
    ), "import_djvu_txt()"
    assert page.export_djvu_txt() == djvu_txt, "export_djvu_txt()"

    #########################

    assert page.export_text() == "The quick brown fox", "export_text()"

    #########################

    pdftext = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title></title>
<meta name="Producer" content="Tesseract 3.03"/>
<meta name="CreationDate" content=""/>
</head>
<body>
<doc>
  <page width="464.910000" height="58.630000">
    <word xMin="1.029000" yMin="22.787000" xMax="87.429570" yMax="46.334000">The</word>
    <word xMin="105.029000" yMin="22.787000" xMax="222.286950" yMax="46.334000">quick</word>
    <word xMin="241.029000" yMin="22.787000" xMax="374.744000" yMax="46.334000">brown</word>
    <word xMin="393.029000" yMin="22.787000" xMax="460.914860" yMax="46.334000">fox</word>
  </page>
</doc>
</body>
</html>
"""
    page.import_pdftotext(pdftext)
    assert (
        page.text_layer == '[{"type": "page", "bbox": [0, 0, 464, 58], "depth": 0}, '
        '{"type": "word", "bbox": [1, 22, 87, 46], "text": "The", "depth": 1}, '
        '{"type": "word", "bbox": [105, 22, 222, 46], "text": "quick", "depth": 1}, '
        '{"type": "word", "bbox": [241, 22, 374, 46], "text": "brown", "depth": 1}, '
        '{"type": "word", "bbox": [393, 22, 460, 46], "text": "fox", "depth": 1}]'
    ), "import_pdftotext()"

    #########################

    page.import_annotations(hocr)
    assert (
        page.annotations
        == '[{"bbox": [0, 0, 422, 61], "type": "page", "id": "page_1", "depth": 0}, '
        '{"bbox": [1, 14, 420, 59], "type": "column", "id": "block_1_1", "depth": 1}, '
        '{"bbox": [1, 14, 420, 59], "baseline": [-0.003, -17], "type": "line", '
        '"id": "line_1_1", "depth": 2}, '
        '{"bbox": [1, 14, 77, 48], "textangle": 90, "confidence": -3, "type": "word", '
        '"id": "word_1_1", "text": "The", "depth": 3}, '
        '{"bbox": [92, 14, 202, 59], "confidence": -3, "type": "word", "id": "word_1_2", '
        '"text": "quick", "depth": 3}, '
        '{"bbox": [214, 14, 341, 48], "confidence": -3, "type": "word", "id": "word_1_3", '
        '"text": "brown", "depth": 3}, '
        '{"bbox": [355, 14, 420, 48], "confidence": -4, "type": "word", "id": "word_1_4", '
        '"text": "fox", "depth": 3}]'
    ), "import_hocr()"

    #########################

    ann = """(maparea "" "()" (rect 157 3030 84 65) (hilite #cccf00) (xor))
"""
    page.import_djvu_ann(ann)
    assert (
        page.annotations == '[{"type": "page", "bbox": [0, 0, 210, 297], "depth": 0}, '
        '{"type": "word", "depth": 1, "text": "()", "bbox": [157, -2798, 241, -2733]}]'
    ), "import_djvu_ann() basic functionality"
    assert page.export_djvu_ann() == ann, "export_djvu_ann()"

    #########################

    pixbuf = page.get_pixbuf_at_scale(100, 100)
    assert isinstance(pixbuf, GdkPixbuf.Pixbuf), "get_pixbuf_at_scale()"

    page.image_object = None
    assert (
        page.get_pixbuf_at_scale(100, 100) is None
    ), "get_pixbuf_at_scale() does fall over with an error"

    #########################

    clean_up_files(["test.pnm", "test.jpg"])