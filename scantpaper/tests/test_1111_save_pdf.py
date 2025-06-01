"Test writing basic PDF"

import datetime
import glob
import locale
import os
from pathlib import Path
import queue
import re
import subprocess
import shutil
import tempfile
import pytest
from gi.repository import GLib
from document import Document
from docthread import DocThread
from basethread import Request
from page import Page


def test_do_save_pdf(clean_up_files):
    "Test writing basic PDF"

    # Create test image
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    thread = DocThread()
    tdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    _number, _thumb, page_id = thread.add_page(
        Page(
            filename="test.pnm",
            dir=tdir.name,
            delete=True,
            format="Portable anymap",
            resolution=(72, 72, "PixelsPerInch"),
            width=70,
            height=46,
        ),
        number=1,
    )
    options = {
        "dir": tdir.name,
        "path": "test.pdf",
        "list_of_pages": [page_id],
        "options": {},
    }
    request = Request("save_pdf", (options,), queue.Queue())
    thread.do_save_pdf(request)
    capture = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
    assert re.search(r"Page size:\s+70 x 46 pts", capture), "valid PDF created"

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.pnm", "test.pdf"]
    )


def test_save_pdf(clean_up_files):
    "Test writing basic PDF"

    # Create test image
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    asserts = 0

    # FIXME: add support for completed, total vars
    #    def import_files_started_cb( thread, process, completed, total ):
    def import_files_started_cb(response):
        nonlocal asserts
        # FIXME: add support for completed/total
        # assert completed== 0, 'completed counter starts at 0'
        # assert total==     2, 'total counter starts at 2'
        assert response.request.process in ["get_file_info", "import_file"]
        asserts += 1

    def import_files_finished_cb(response):
        nonlocal asserts
        assert not slist.thread.pages_saved(), "pages not tagged as saved"
        asserts += 1
        mlp.quit()

    slist.import_files(
        paths=["test.pnm"],
        started_callback=import_files_started_cb,
        finished_callback=import_files_finished_cb,
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    # FIXME: add support for completed, total vars
    #    def save_pdf_started_cb( result, completed, total ):
    def save_pdf_started_cb(result):
        nonlocal asserts
        assert result.request.process == "save_pdf", "save_pdf"
        # FIXME: add support for completed/total
        # assert completed== 0, 'completed counter re-initialised'
        # assert total==     1, 'total counter re-initialised'
        asserts += 1

    def save_pdf_finished_cb(result):
        nonlocal asserts
        capture = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
        assert (
            re.search(r"Page size:\s+70 x 46 pts", capture) is not None
        ), "valid PDF created"
        assert slist.thread.pages_saved(), "pages tagged as saved"
        asserts += 1
        mlp.quit()

    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        options={
            "post_save_hook": "pdftoppm %i test",
            "post_save_hook_options": "fg",
        },
        started_callback=save_pdf_started_cb,
        finished_callback=save_pdf_finished_cb,
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert asserts == 5, "ran all callbacks"

    capture = subprocess.check_output(["identify", "test-1.ppm"], text=True)
    assert re.search(
        r"test-1.ppm PPM 146x96 146x96\+0\+0 8-bit sRGB", capture
    ), "ran post-save hook on pdf"

    #########################

    clean_up_files(
        [
            Path(tempfile.gettempdir()) / "document.db",
            "test.png",
            "test.pnm",
            "test.pdf",
            "test-1.ppm",
        ]
    )


def test_save_pdf_with_locale(import_in_mainloop, clean_up_files):
    "Test with non-English locale"
    locale.setlocale(locale.LC_NUMERIC, "de_DE.utf8")

    # Create test image
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    import_in_mainloop(slist, ["test.pnm"])

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        finished_callback=mlp.quit,
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
    assert (
        re.search(r"Page size:\s+70 x 46 pts", capture) is not None
    ), "valid PDF created"

    #########################

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.pnm", "test.pdf"]
    )


def test_save_pdf_with_error(import_in_mainloop, clean_up_files):
    "Test saving a PDF and triggering an error"

    # Create test image
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()
    asserts = 0

    import_in_mainloop(slist, ["test.pnm"])

    # inject error before save_pdf
    os.chmod(dirname.name, 0o500)  # no write access

    def error_callback1(_page, _process, _message):
        "no write access"
        assert True, "caught error injected before save_pdf"
        nonlocal asserts
        asserts += 1
        mlp.quit()

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        error_callback=error_callback1,
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    def error_callback2(_page, _process, _message):
        assert True, "save_pdf caught error injected in queue"
        os.chmod(dirname.name, 0o700)  # allow write access
        nonlocal asserts
        asserts += 1
        mlp.quit()

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        error_callback=error_callback2,
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 2, "ran all callbacks"

    #########################

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.pnm", "test.pdf"]
    )


def test_save_pdf_different_resolutions(import_in_mainloop, clean_up_files):
    "test saving a PDF with different resolutions in the height and width directions"

    # Create test image
    subprocess.run(["convert", "rose:", "-density", "100x200", "test.png"], check=True)

    slist = Document()

    import_in_mainloop(slist, ["test.png"])

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
    assert (
        re.search(r"Page size:\s+50.4 x 16.56 pts", capture) is not None
    ), "valid PDF created"

    #########################

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.png", "test.pdf"]
    )


def test_save_encrypted_pdf(import_in_mainloop, clean_up_files):
    "test saving an encrypted PDF"
    if shutil.which("pdftk") is None:
        pytest.skip("pdftk not found")
        return

    # Create test image
    subprocess.run(["convert", "rose:", "test.jpg"], check=True)

    slist = Document()

    import_in_mainloop(slist, ["test.jpg"])

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        options={"user-password": "123"},
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    with pytest.raises(subprocess.CalledProcessError):
        subprocess.check_output(["pdfinfo", "test.pdf"])

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.jpg", "test.pdf"]
    )


def test_save_pdf_with_hocr(import_in_mainloop, clean_up_files):
    "Test writing PDF with text layer from hocr"

    # Create test image
    subprocess.run(
        [
            "convert",
            "+matte",
            "-depth",
            "1",
            "-colorspace",
            "Gray",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-units",
            "PixelsPerInch",
            "-density",
            "300",
            "label:The quick brown fox",
            "-border",
            "20x10",
            "test.png",
        ],
        check=True,
    )
    info = subprocess.check_output(["identify", "test.png"], text=True)
    width, height = None, None
    regex = re.search(r"(\d+)+x(\d+)", info)
    if regex:
        width, height = regex.group(1), regex.group(2)

    slist = Document()

    import_in_mainloop(slist, ["test.png"])

    hocr = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title></title>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>
  <meta name='ocr-system' content='tesseract 4.1.1' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word ocrp_wconf'/>
 </head>
 <body>
  <div class='ocr_page' id='page_1' title='image "test.png"; bbox 0 0 550 80; ppageno 0'>
   <div class='ocr_carea' id='block_1_1' title="bbox 20 19 527 67">
    <p class='ocr_par' id='par_1_1' lang='eng' title="bbox 20 19 527 67">
     <span class='ocr_line' id='line_1_1' title="bbox 20 19 527 67; baseline 0 -10; x_size 47; x_descenders 9; x_ascenders 10">
      <span class='ocrx_word' id='word_1_1' title='bbox 20 19 112 58; x_wconf 95'>The</span>
      <span class='ocrx_word' id='word_1_2' title='bbox 132 19 264 67; x_wconf 96'>quick</span>
      <span class='ocrx_word' id='word_1_3' title='bbox 284 19 432 58; x_wconf 95'>brown</span>
      <span class='ocrx_word' id='word_1_4' title='bbox 453 19 527 58; x_wconf 96'>fox</span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    page = slist.thread.get_page(id=1)
    page.import_hocr(hocr)
    slist.thread.set_text(1, page.text_layer)
    #    slist.data[0][2].import_annotations(hocr)

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    import_in_mainloop(slist, ["test.pdf"])

    # Because we cannot reproduce the exact typeface used
    # in the original, we cannot expect to be able to
    # round-trip the text layer. Here, at least we can check
    # that we have scaled the page size correctly.
    page = slist.thread.get_page(id=2)
    assert (
        re.search(rf"bbox\s0\s0\s{width}\s{height}", page.export_hocr()) is not None
    ), "import text layer"
    # assert re.search(r"The.+quick.+brown.+fox", slist.data[1][2].annotations) \
    #     is not None, 'import annotations'

    capture = subprocess.check_output(["pdftotext", "test.pdf", "-"], text=True)
    assert re.search(
        r"The.*quick.*brown.*fox", capture, re.DOTALL
    ), "PDF with expected text"
    # capture = subprocess.check_output(["cat","test.pdf"], text=True)
    # assert re.search(r"/Type\s/Annot\s/Subtype\s/Highlight\s/C.+/Contents.+fox",
    #                  capture) is not None, 'PDF with expected annotation'

    #########################

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.png", "test.pdf"]
    )


@pytest.mark.skip(reason="OCRmyPDF doesn't yet support non-latin characters")
def test_save_pdf_with_utf8(import_in_mainloop, clean_up_files):
    "Test writing PDF with utf8 in text layer"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)
    options = {}

    # To avoid piping one into the other. See
    # https://stackoverflow.com/questions/13332268/how-to-use-subprocess-command-with-pipes
    with subprocess.Popen(
        ("fc-list", ":lang=ru", "file"), stdout=subprocess.PIPE
    ) as fcl:
        with subprocess.Popen(
            ("grep", "ttf"), stdin=fcl.stdout, stdout=subprocess.PIPE
        ) as grep:
            options["font"] = subprocess.check_output(
                ("head", "-n", "1"), stdin=grep.stdout, text=True
            )
            fcl.wait()
            grep.wait()
            options["font"] = options["font"].rstrip()
            options["font"] = re.sub(r":\s*$", r"", options["font"], count=1)

    slist = Document()

    import_in_mainloop(slist, ["test.pnm"])

    slist.thread.set_text(
        1,
        '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
        '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
        '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
        '{"bbox": [1, 14, 77, 48], "type": "word", "text": '
        '"пени способствовала сохранению", "depth": 3}]',
    )

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        options={"options": options},
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    out = subprocess.check_output(["pdftotext", "test.pdf", "-"], text=True)
    assert (
        re.search(r"пени способствовала сохранению", out) is not None
    ), "PDF with expected text"

    #########################

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.pnm", "test.pdf"]
    )


@pytest.mark.skip(reason="OCRmyPDF doesn't yet support non-latin characters")
def test_save_pdf_with_non_utf8(import_in_mainloop, clean_up_files):
    "Test writing PDF with non-utf8 in text layer"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    import_in_mainloop(slist, ["test.pnm"])

    slist.thread.set_text(
        1,
        '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
        '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
        '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
        '{"bbox": [1, 14, 77, 48], "type": "word", "text": "P�e", "depth": 3}]',
    )
    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    out = subprocess.check_output(["pdftotext", "test.pdf", "-"], text=True)
    assert re.search(r"P■e■", out) is not None, "PDF with expected text"

    #########################

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.pnm", "test.pdf"]
    )


def test_save_pdf_with_1bpp(import_in_mainloop, clean_up_files):
    "Test writing PDF with a 1bpp image"

    subprocess.run(["convert", "magick:netscape", "test.pbm"], check=True)

    slist = Document()

    import_in_mainloop(slist, ["test.pbm"])

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    subprocess.run(["pdfimages", "test.pdf", "x"], check=True)
    out = subprocess.check_output(["identify", "x-000.p*m"], text=True)
    assert re.search(r"1-bit Bilevel Gray", out), "PDF with 1bpp created"

    #########################

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.pbm", "test.pdf"]
        + glob.glob("x-000.p*m")
    )


@pytest.mark.skip(reason="OCRmyPDF doesn't yet support non-latin characters")
def test_save_pdf_without_font(import_in_mainloop, clean_up_files):
    "Test writing PDF with non-existing font"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    import_in_mainloop(slist, ["test.pnm"])

    slist.thread.set_text(
        1,
        '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
        '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
        '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
        '{"bbox": [1, 14, 77, 48], "type": "word", "text": "äöü", "depth": 3}]',
    )
    asserts = 0

    def error_callback(response):
        nonlocal asserts
        assert response.info == "Save file", "expected process"
        assert (
            response.status == "Unable to find font 'removed'. Defaulting to core font."
        ), "expected error message"
        asserts += 1

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        options={"options": {"font": "removed"}},
        error_callback=error_callback,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    out = subprocess.check_output(["pdftotext", "test.pdf", "-"], text=True)
    assert re.search(r"äöü", out) is not None, "PDF with expected text"
    assert asserts == 1, "ran all callbacks"

    #########################

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.pnm", "test.pdf"]
    )


def test_save_pdf_g4(import_in_mainloop, clean_up_files):
    "Test writing PDF with group 4 compression"

    subprocess.run(["convert", "rose:", "test.png"], check=True)

    slist = Document()

    import_in_mainloop(slist, ["test.png"])

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        options={
            "compression": "g4",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    subprocess.run(["pdfimages", "test.pdf", "x"], check=True)
    out = subprocess.check_output(["identify", "x-000.p*m"], text=True)
    assert (
        re.search(r"1-bit Bilevel Gray", out) is not None
    ), "PDF with 1bpp created from 8-bit image"

    #########################

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.png", "test.pdf"]
        + glob.glob("x-000.p*m")
    )


def test_save_pdf_g4_alpha(import_in_mainloop, clean_up_files):
    "Test writing PDF with group 4 compression"

    subprocess.run(
        [
            "convert",
            "rose:",
            "-define",
            "tiff:rows-per-strip=1",
            "-compress",
            "group4",
            "test.tif",
        ],
        check=True,
    )

    slist = Document()

    import_in_mainloop(slist, ["test.tif"])

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        options={
            "compression": "g4",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    subprocess.run(
        [
            "gs",
            "-q",
            "-dNOPAUSE",
            "-dBATCH",
            "-sDEVICE=pnggray",
            "-g70x46",
            "-dPDFFitPage",
            "-dUseCropBox",
            "-sOutputFile=test.png",
            "test.pdf",
        ],
        check=True,
    )
    example = subprocess.check_output(
        ["convert", "test.png", "-depth", "1", "-alpha", "off", "txt:-"], text=True
    )
    expected = subprocess.check_output(
        ["convert", "test.tif", "-depth", "1", "-alpha", "off", "txt:-"], text=True
    )
    assert example == expected, "valid G4 PDF created from multi-strip TIFF"

    #########################

    clean_up_files(
        [
            Path(tempfile.gettempdir()) / "document.db",
            "test.tif",
            "test.png",
            "test.pdf",
        ]
    )


def test_save_pdf_with_sbs_hocr(import_in_mainloop, clean_up_files):
    "Test writing PDF with text layer right of the image, rather than behind it"

    subprocess.run(
        [
            "convert",
            "+matte",
            "-depth",
            "1",
            "-colorspace",
            "Gray",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-units",
            "PixelsPerInch",
            "-density",
            "300",
            "label:The quick brown fox",
            "-border",
            "20x10",
            "test.png",
        ],
        check=True,
    )
    info = subprocess.check_output(["identify", "test.png"], text=True)
    width, height = None, None
    regex = re.search(r"(\d+)+x(\d+)", info)
    if regex:
        width, height = regex.group(1), regex.group(2)

    slist = Document()

    import_in_mainloop(slist, ["test.png"])

    hocr = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title>
</title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='tesseract 3.03' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word'/>
</head>
<body>
  <div class='ocr_page' id='page_1' title='image "test.png"; bbox 0 0 452 57; ppageno 0'>
   <div class='ocr_carea' id='block_1_1' title="bbox 1 9 449 55">
    <p class='ocr_par' dir='ltr' id='par_1_1' title="bbox 1 9 449 55">
     <span class='ocr_line' id='line_1_1' title="bbox 1 9 449 55; baseline 0 -10">
      <span class='ocrx_word' id='word_1_1' title='bbox 1 9 85 45; x_wconf 90' lang='eng' dir='ltr'>The</span>
      <span class='ocrx_word' id='word_1_2' title='bbox 103 9 217 55; x_wconf 89' lang='eng' dir='ltr'>quick</span>
      <span class='ocrx_word' id='word_1_3' title='bbox 235 9 365 45; x_wconf 94' lang='eng' dir='ltr'>brown</span>
      <span class='ocrx_word' id='word_1_4' title='bbox 383 9 449 45; x_wconf 94' lang='eng' dir='ltr'>fox</span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    page = slist.thread.get_page(id=1)
    page.import_hocr(hocr)
    slist.thread.set_text(1, page.text_layer)

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        options={"text_position": "right"},
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["pdftotext", "test.pdf", "-"], text=True)
    assert re.search(
        r"The.*quick.*brown.*fox", example, re.DOTALL
    ), "PDF with expected text"

    import_in_mainloop(slist, ["test.pdf"])

    # Because we cannot reproduce the exact typeface used
    # in the original, we cannot expect to be able to
    # round-trip the text layer. Here, at least we can check
    # that we have scaled the page size correctly.
    page = slist.thread.get_page(id=2)
    assert (
        re.search(rf"bbox\s0\s0\s{width}\s{height}", page.export_hocr()) is not None
    ), "import text layer"

    #########################

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.png", "test.pdf"]
    )


def test_save_pdf_with_metadata(import_in_mainloop, clean_up_files):
    "Test writing PDF with metadata"

    pnm = "test.pnm"
    pdf = "test.pdf"
    subprocess.run(["convert", "rose:", pnm], check=True)

    slist = Document()

    import_in_mainloop(slist, [pnm])

    metadata = {
        "datetime": datetime.datetime(2016, 2, 10, 0, 0, tzinfo=datetime.timezone.utc),
        "title": "metadata title",
        "subject": "",
    }
    mlp = GLib.MainLoop()
    slist.save_pdf(
        path=pdf,
        list_of_pages=[slist.data[0][2]],
        metadata=metadata,
        options={"set_timestamp": True},
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    info = subprocess.check_output(["pdfinfo", "-isodates", pdf], text=True)
    assert re.search(r"metadata title", info) is not None, "metadata title in PDF"

    assert re.search(r"NONE", info) is None, "don't add blank metadata"

    assert re.search(r"2016-02-10T00:00:00Z", info), "metadata ModDate in PDF"
    stb = os.stat(pdf)
    assert datetime.datetime.utcfromtimestamp(stb.st_mtime) == datetime.datetime(
        2016, 2, 10, 0, 0, 0
    ), "timestamp"

    #########################

    clean_up_files([Path(tempfile.gettempdir()) / "document.db", pnm, pdf])


def test_save_pdf_with_old_metadata(import_in_mainloop, clean_up_files):
    "Test writing PDF with old metadata"

    pnm = "test.pnm"
    pdf = "test.pdf"
    subprocess.run(["convert", "rose:", pnm], check=True)

    slist = Document()

    import_in_mainloop(slist, [pnm])

    metadata = {
        "datetime": datetime.datetime(1966, 2, 10, 0, 0, tzinfo=datetime.timezone.utc),
        "title": "metadata title",
    }

    called = False

    def error_callback(_result):
        nonlocal called
        called = True

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path=pdf,
        list_of_pages=[slist.data[0][2]],
        metadata=metadata,
        options={"set_timestamp": True},
        finished_callback=lambda response: mlp.quit(),
        error_callback=error_callback,
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert called, "caught errors setting timestamp"

    info = subprocess.check_output(["pdfinfo", "-isodates", pdf], text=True)
    assert (
        re.search(r"1966-02-10T00:00:00Z", info) is not None
    ), "metadata ModDate in PDF"

    #########################

    clean_up_files([Path(tempfile.gettempdir()) / "document.db", pnm, pdf])


def test_save_pdf_with_downsample(import_in_mainloop, clean_up_files):
    "Test writing PDF with downsampled image"

    subprocess.run(
        [
            "convert",
            "+matte",
            "-depth",
            "1",
            "-colorspace",
            "Gray",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-density",
            "300",
            "label:The quick brown fox",
            "test.png",
        ],
        check=True,
    )

    slist = Document()

    import_in_mainloop(slist, ["test.png"])

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test2.pdf",
        list_of_pages=[slist.data[0][2]],
        options={
            "downsample": True,
            "downsample dpi": 150,
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert os.path.getsize("test.pdf") > os.path.getsize(
        "test2.pdf"
    ), "downsampled PDF smaller than original"

    subprocess.run(["pdfimages", "test2.pdf", "x"], check=True)
    example = subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", "x-000.pbm"], text=True
    )
    assert re.search(
        r"PBM 2\d\dx[23]\d 2\d\dx[23]\d[+]0[+]0 1-bit DirectClass Gray", example
    ), "downsampled"

    #########################

    clean_up_files(
        [
            Path(tempfile.gettempdir()) / "document.db",
            "test.png",
            "test.pdf",
            "test2.pdf",
            "x-000.pbm",
        ]
    )


def test_cancel_save_pdf(import_in_mainloop, clean_up_files):
    "Test writing PDF with downsampled image"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    import_in_mainloop(slist, ["test.pnm"])

    def finished_callback(_response):
        assert False, "Finished callback"

    mlp = GLib.MainLoop()
    called = False

    def cancelled_callback(_response):
        nonlocal called
        called = True
        mlp.quit()

    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        finished_callback=finished_callback,
    )
    slist.cancel(cancelled_callback)
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    slist.save_image(
        path="test.jpg",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert subprocess.check_output(
        ["identify", "test.jpg"], text=True
    ), "can create a valid JPG after cancelling save PDF process"

    #########################

    clean_up_files(
        [
            Path(tempfile.gettempdir()) / "document.db",
            "test.pnm",
            "test.pdf",
            "test.jpg",
        ]
    )
