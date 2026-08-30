"Tests for Page class"

# pylint: disable=protected-access  # tests access private members

import io
import os
import subprocess
import tempfile

import config
import pytest
from const import VERSION
from gi.repository import GdkPixbuf
from helpers import Proc
from page import Page, _prepare_scale
from PIL import Image


def test_1(temp_pnm, temp_jpg):
    "Tests for Page class"
    with pytest.raises(TypeError):
        page = Page(image_object=None)
    with tempfile.TemporaryDirectory() as dirname:
        with pytest.raises(ValueError, match="please supply either"):
            page = Page(dir=dirname)
        os.remove(temp_pnm.name)
        with pytest.raises(FileNotFoundError):
            page = Page(filename=temp_pnm.name, format="PBM", dir=dirname)

        # Create test image
        subprocess.run(
            [config.CONVERT_COMMAND, "-size", "210x297", "xc:white", temp_pnm.name],
            check=True,
        )
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

        page = Page(image_object=image_object, dir=dirname)
        assert page.matching_paper_sizes(paper_sizes) == {
            "A4": 25.4
        }, "from image object"

        page = Page(filename=temp_pnm.name, dir=dirname)
        assert page.matching_paper_sizes(paper_sizes) == {"A4": 25.4}, "basic portrait"
        page = Page(filename=temp_pnm.name, dir=dirname)
        assert page.matching_paper_sizes(paper_sizes) == {"A4": 25.4}, "basic landscape"

        #########################

        assert page.get_resolution(paper_sizes) == (
            25.4,
            25.4,
            "PixelsPerInch",
        ), "resolution"

        subprocess.run(
            [
                config.CONVERT_COMMAND,
                "-units",
                "PixelsPerInch",
                "-density",
                "300",
                "xc:white",
                temp_jpg.name,
            ],
            check=True,
        )
        page = Page(filename=temp_jpg.name, dir=dirname)
        assert page.get_resolution(paper_sizes) == (
            300.0,
            300.0,
            "PixelsPerInch",
        ), "inches"

        subprocess.run(
            [
                config.CONVERT_COMMAND,
                "-units",
                "PixelsPerCentimeter",
                "-density",
                "118",
                "xc:white",
                temp_jpg.name,
            ],
            check=True,
        )
        page = Page(filename=temp_jpg.name, dir=dirname)
        assert page.get_resolution(paper_sizes) == (
            299.72,
            299.72,
            "PixelsPerCentimeter",
        ), "centimetres"

        subprocess.run(
            [
                config.CONVERT_COMMAND,
                "-units",
                "Undefined",
                "-density",
                "300",
                "xc:white",
                temp_jpg.name,
            ],
            check=True,
        )
        page = Page(filename=temp_jpg.name, dir=dirname)
        assert page.get_resolution(paper_sizes) == (
            300.0,
            300.0,
            "PixelsPerInch",
        ), "undefined"

        #########################

        assert _prepare_scale(1000, 100, 1, 100, 100) == (100, 10.0), "scale x, ratio 1"
        assert _prepare_scale(100, 1000, 1, 100, 100) == (10, 100.0), "scale y, ratio 1"
        assert _prepare_scale(1000, 100, 2, 100, 100) == (100, 20.0), "scale x, ratio 2"
        assert _prepare_scale(100, 1000, 2, 100, 100) == (5, 100.0), "scale y, ratio 2"
        assert _prepare_scale(0, 1000, 2, 100, 100) == (None, None), "invalid"

        #########################

        assert page.export_djvu_txt() is None, "export_djvu_txt() without bboxes"
        assert page.export_text() == "", "export_text() without bboxes"
        assert page.export_djvu_ann() is None, "export_djvu_ann() without bboxes"
        page.text_layer = ""
        assert (
            page._add_txt_to_djvu("file.djvu", dirname) is None
        ), "_add_txt_to_djvu() without bboxes"
        page.annotations = ""
        assert (
            page._add_ann_to_djvu("file.djvu", dirname) is None
        ), "_add_ann_to_djvu() without bboxes"


def test_2(temp_pnm):
    "Tests for Page class"

    subprocess.run(
        [config.CONVERT_COMMAND, "-size", "210x297", "xc:white", temp_pnm.name],
        check=True,
    )

    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=temp_pnm.name,
            dir=dirname,
            size=[105, 148, "elephants"],
        )
        with pytest.raises(ValueError, match="unknown units"):
            page.get_resolution()

        page = Page(
            filename=temp_pnm.name,
            dir=dirname,
            size=[105, 148, "pts"],
        )
        assert page.get_resolution() == (
            144.0,
            144.48648648648648,
            "PixelsPerInch",
        ), "from pdfinfo paper size"

        page = Page(
            filename=temp_pnm.name,
            dir=dirname,
        )
        assert page.get_resolution() == (72, 72, "PixelsPerInch"), "default to 72"

        #########################

        hocr = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='scantpaper {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' id='page_1' title='bbox 0 0 422 61'>
   <div class='ocr_carea' id='block_1_1' title='bbox 1 14 420 59'>
    <span class='ocr_line' id='line_1_1' title='bbox 1 14 420 59; baseline -0.003 -17'>
     <span class='ocrx_word' id='word_1_1' title='bbox 1 14 77 48; textangle 90; x_wconf -3'>The</span>
     <span class='ocrx_word' id='word_1_2' title='bbox 92 14 202 59; x_wconf -3'>quick</span>
     <span class='ocrx_word' id='word_1_3' title='bbox 214 14 341 48; x_wconf -3'>brown</span>
     <span class='ocrx_word' id='word_1_4' title='bbox 355 14 420 48; x_wconf -4'>fox</span>
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
            '{"bbox": [1, 14, 420, 59], "baseline": [-0.003, -17], "type": "line", '
            '"id": "line_1_1", "depth": 2}, {"bbox": [1, 14, 77, 48], "textangle": 90, '
            '"confidence": -3, "type": "word", "id": "word_1_1", "text": "The", "depth": 3}, '
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
            page.text_layer == '[{"depth": 0, "type": "page", "bbox": [0, 0, 422, 61], '
            '"text": "The quick brown fox"}]'
        ), "import_djvu_txt()"
        assert page.export_djvu_txt() == djvu_txt, "export_djvu_txt()"

        #########################

        assert page.export_text() == "The quick brown fox", "export_text()"

        #########################

        pdftext = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>red</title>
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
            page.text_layer
            == '[{"type": "page", "bbox": [0, 0, 464, 58], "depth": 0}, '
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
            page.annotations
            == '[{"type": "page", "bbox": [0, 0, 210, 297], "depth": 0}, '
            '{"type": "word", "depth": 1, "text": "()", "bbox": [157, -2798, 241, -2733]}]'
        ), "import_djvu_ann() basic functionality"
        assert page.export_djvu_ann() == ann, "export_djvu_ann()"

        #########################

        pixbuf = page.get_pixbuf()
        assert isinstance(pixbuf, GdkPixbuf.Pixbuf), "get_pixbuf()"

        pixbuf = page.get_pixbuf_at_scale(100, 100)
        assert isinstance(pixbuf, GdkPixbuf.Pixbuf), "get_pixbuf_at_scale()"

        page.image_object = None
        assert page.get_pixbuf() is None, "get_pixbuf() doesn't fall over with an error"
        assert (
            page.get_pixbuf_at_scale(100, 100) is None
        ), "get_pixbuf_at_scale() doesn't fall over with an error"


def test_get_pixbuf_error(mocker):
    "Test error handling in get_pixbuf()"
    mocker.patch("page.GdkPixbuf.Pixbuf.new_from_file", side_effect=TypeError)
    mocker.patch("page.GdkPixbuf.Pixbuf.new_from_file_at_scale", side_effect=TypeError)
    page = Page(image_object=Image.new("RGB", (210, 297)))
    assert page.get_pixbuf() is None, "TypeError from Pixbuf.new_from_file not caught"
    assert (
        page.get_pixbuf_at_scale(1, 1) is None
    ), "TypeError from Pixbuf.new_from_file_at_scale not caught"


def test_write_image_for_djvu():
    "Test write_image_for_djvu()"
    with (
        tempfile.TemporaryDirectory() as dirname,
        tempfile.NamedTemporaryFile(suffix=".pbm") as filename,
    ):
        page = Page(image_object=Image.new("1", (210, 297)))
        page.write_image_for_djvu(filename.name, {"dir": dirname, "pidfile": None})
        assert os.path.isfile(filename.name), "write_image_for_djvu() creates a file"


def test_write_image_for_tiff():
    "Test write_image_for_djvu()"
    with (
        tempfile.TemporaryDirectory() as dirname,
        tempfile.NamedTemporaryFile(suffix=".tif") as filename,
    ):
        page = Page(image_object=Image.new("RGB", (210, 297)))
        page.resolution = (300, 300, "PixelsPerInch")
        page.write_image_for_tiff(
            filename.name, {"dir": dirname, "options": {"compression": "jpeg"}}
        )
        assert os.path.isfile(filename.name), "write_image_for_tiff() creates a file"


def test_write_image_for_djvu_error(mocker):
    "Test error handling in write_image_for_djvu()"
    with (
        tempfile.TemporaryDirectory() as dirname,
        tempfile.NamedTemporaryFile(suffix=".pbm") as filename,
    ):
        mock_exec = mocker.patch("page.exec_command")
        mock_exec.return_value = Proc(
            returncode=1, stdout="", stderr="compression error"
        )
        page = Page(image_object=Image.new("1", (210, 297)))
        # This should log an error but not raise an exception
        page.write_image_for_djvu(filename.name, {"dir": dirname, "pidfile": None})
        mock_exec.assert_called_once()


def test_import_hocr_empty():
    "Test that importing empty hOCR sets text_layer to None"

    empty_hocr = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='scantpaper {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
 </body>
</html>
"""
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(image_object=Image.new("RGB", (210, 297)), dir=dirname)
        page.import_hocr(empty_hocr)
        assert page.text_layer is None, "empty hOCR should set text_layer to None"


def test_to_stored_bytes_grayscale_tiff_is_jpeg(temp_tif):
    "continuous-tone TIFF pages are stored as JPEG"
    Image.new("L", (210, 297), 128).save(temp_tif.name)
    page = Page(filename=temp_tif.name)
    stored = page.to_stored_bytes()
    assert Image.open(io.BytesIO(stored)).format == "JPEG"


def test_to_stored_bytes_bilevel_is_png(temp_tif):
    "1-bit pages are stored losslessly as PNG"
    Image.new("1", (210, 297), 0).save(temp_tif.name)
    page = Page(filename=temp_tif.name)
    stored = page.to_stored_bytes()
    assert Image.open(io.BytesIO(stored)).format == "PNG"


def test_to_stored_bytes_rgba_is_png():
    "images with an alpha channel are stored losslessly"
    page = Page(image_object=Image.new("RGBA", (210, 297)))
    stored = page.to_stored_bytes()
    image = Image.open(io.BytesIO(stored))
    assert image.format == "PNG"
    assert image.mode == "RGBA"


def test_to_stored_bytes_jpeg_file_passthrough(temp_jpg):
    "importing a JPEG file stores the original bytes"
    Image.new("RGB", (210, 297)).save(temp_jpg.name, format="JPEG")
    with open(temp_jpg.name, "rb") as fhd:
        original = fhd.read()
    page = Page(filename=temp_jpg.name)
    assert page.to_stored_bytes() == original


def test_to_stored_bytes_png_file_passthrough(temp_png):
    "importing a PNG file stores the original bytes"
    Image.new("RGB", (210, 297)).save(temp_png.name, format="PNG")
    with open(temp_png.name, "rb") as fhd:
        original = fhd.read()
    page = Page(filename=temp_png.name)
    assert page.to_stored_bytes() == original


def test_get_pixbuf_at_scale_downscales_before_save(mocker):
    "thumbnails are produced from a downscaled image, not a full-size one"
    page = Page(image_object=Image.new("RGB", (1000, 1000)))
    saved_sizes = []
    original_save = Image.Image.save

    def spy_save(self, fp, *args, **kwargs):
        saved_sizes.append(self.size)
        return original_save(self, fp, *args, **kwargs)

    mocker.patch.object(Image.Image, "save", spy_save)
    pixbuf = page.get_pixbuf_at_scale(100, 100)
    assert pixbuf is not None, "get_pixbuf_at_scale()"
    assert pixbuf.get_width() == 100, "downscaled pixbuf width"
    assert pixbuf.get_height() == 100, "downscaled pixbuf height"
    assert saved_sizes == [(100, 100)], "image downscaled before save"


def test_write_image_for_pdf_passthrough():
    "stored JPEG bytes are written to the PDF without re-encoding"
    buf = io.BytesIO()
    Image.new("RGB", (210, 297)).save(buf, format="JPEG", quality=92)
    stored = buf.getvalue()
    page = Page.from_bytes(stored)
    page.resolution = (72, 72, "PixelsPerInch")
    with tempfile.NamedTemporaryFile(suffix=".png") as filename:
        page.write_image_for_pdf(filename.name, None)
        with open(filename.name, "rb") as fhd:
            assert fhd.read() == stored, "bytes passed through"


def test_write_image_for_pdf_reenocodes_with_options():
    "downsampling or compression forces a re-encode"
    buf = io.BytesIO()
    Image.new("RGB", (210, 297)).save(buf, format="JPEG", quality=92)
    stored = buf.getvalue()
    page = Page.from_bytes(stored)
    page.resolution = (72, 72, "PixelsPerInch")
    with tempfile.NamedTemporaryFile(suffix=".png") as filename:
        options = {"options": {"downsample": True, "downsample dpi": 36}}
        page.write_image_for_pdf(filename.name, options)
        with open(filename.name, "rb") as fhd:
            output = fhd.read()
        assert output != stored, "downsampled image re-encoded"
        assert Image.open(io.BytesIO(output)).size == (105, 148), "downsampled size"
    with tempfile.NamedTemporaryFile(suffix=".png") as filename:
        options = {"options": {"compression": "g4"}}
        page.write_image_for_pdf(filename.name, options)
        with open(filename.name, "rb") as fhd:
            output = fhd.read()
        assert output != stored, "compressed image re-encoded"
        assert Image.open(io.BytesIO(output)).mode == "1", "thresholded to bilevel"


def test_from_bytes_png_blob_readable():
    "PNG blobs from sessions before this change remain readable"
    img = Image.new("RGB", (210, 297))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    page = Page.from_bytes(buf.getvalue(), id=1)
    assert page.image_object.format == "PNG", "stored format detected"
    assert page.get_size() == (210, 297), "page size read from blob"
    assert isinstance(page.get_pixbuf(), GdkPixbuf.Pixbuf), "PNG blob displays"
