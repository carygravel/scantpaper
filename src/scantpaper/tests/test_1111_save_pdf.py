"""Test writing basic PDF."""

from __future__ import annotations

import datetime
import locale
import pathlib
import queue
import re
import shutil
import subprocess
import tempfile
import threading
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import img2pdf
import pikepdf
import pytest
from PIL import Image, features

from scantpaper import config
from scantpaper.basethread import Request, Response
from scantpaper.const import POINTS_PER_INCH
from scantpaper.dependencies import jbig2_available
from scantpaper.docthread import DocThread
from scantpaper.document import Document
from scantpaper.loop_helpers import safe_mainloop
from scantpaper.page import Page

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


def has_locale(name: str) -> bool:
    """Check if the given locale is available on the system."""
    try:
        old_locale = locale.setlocale(locale.LC_CTYPE)
        locale.setlocale(locale.LC_CTYPE, name)
        locale.setlocale(locale.LC_CTYPE, old_locale)
    except locale.Error:
        return False
    else:
        return True


def get_page_size(path: str) -> tuple[float, float]:
    """Get page size from PDF using pikepdf. Returns (width, height) in points."""
    with pikepdf.open(path) as pdf:
        page = pdf.pages[0]
        width = float(page.MediaBox[2]) - float(page.MediaBox[0])
        height = float(page.MediaBox[3]) - float(page.MediaBox[1])
        return width, height


def _page_content(page: pikepdf.Page) -> bytes:
    """Return a page's decoded content stream bytes."""
    contents = page.obj.get("/Contents")
    return bytes(cast("pikepdf.Stream", contents).read_bytes())


def _form_xobject_streams(
    resources: object, seen: set[tuple[int, int]]
) -> Iterator[bytes]:
    """Yield decoded content streams from recursive Form XObjects."""
    if not isinstance(resources, pikepdf.Dictionary):
        return
    xobjects = resources.get("/XObject")
    if not isinstance(xobjects, pikepdf.Dictionary):
        return
    for obj in dict(xobjects).values():
        if not isinstance(obj, pikepdf.Stream):
            continue
        if obj.get("/Subtype") != pikepdf.Name("/Form"):
            continue
        key = obj.objgen if obj.objgen != (0, 0) else (id(obj), 0)
        if key in seen:
            continue
        seen.add(key)
        yield bytes(obj.read_bytes())
        yield from _form_xobject_streams(obj.get("/Resources"), seen)


def _page_content_streams(page: pikepdf.Page) -> list[bytes]:
    """Return the page content and every Form XObject content stream."""
    forms = _form_xobject_streams(page.obj.get("/Resources"), set())
    return [_page_content(page), *forms]


def _has_rotated_text(content: bytes) -> bool:
    """Return whether text is rotated by a Tm or a surrounding cm."""
    if not re.search(rb"\bBT\b", content):
        return False
    pattern = re.compile(
        rb"([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)"
        rb"\s+([-\d.]+)\s+([-\d.]+)\s+(?:Tm|cm)"
    )
    for match in pattern.finditer(content):
        _a, b, c, _d, _e, _f = (float(value) for value in match.groups())
        if abs(b) > 1e-6 or abs(c) > 1e-6:
            return True
    return False


def _write_large_bilevel(path: str) -> None:
    """Write a page-sized bilevel image with a substantial CCITT stream.

    OCRmyPDF's PDF/A step (Ghostscript) inlines very small images, which would
    leave the post-embed JBIG2 pass nothing to convert, so the JBIG2 tests must
    use a realistically sized page.
    """
    subprocess.run(
        [
            config.CONVERT_COMMAND,
            "-size",
            "2480x3508",
            "xc:white",
            "-fill",
            "black",
            "-pointsize",
            "120",
            "-annotate",
            "+100+300",
            "scantpaper JBIG2 test page",
            "-threshold",
            "50%",
            "-type",
            "bilevel",
            path,
        ],
        check=True,
    )


def _ccitt_group(parms: object) -> str:
    """Return ``Group4`` for a negative CCITT ``/K``, otherwise ``Group3``.

    ``/DecodeParms`` is a dictionary for a bare filter and an array when the
    filter itself is an array (img2pdf's XObject form).
    """
    if isinstance(parms, pikepdf.Array):
        entries: list[object] = [parms[i] for i in range(len(parms))]
    elif parms is None:
        entries = []
    else:
        entries = [parms]
    for entry in entries:
        if isinstance(entry, pikepdf.Dictionary):
            k = entry.get("/K")
            if k is not None and int(k) < 0:
                return "Group4"
    return "Group3"


def get_pdf_image_codecs(path: str) -> list[str]:
    """Return the codecs used by every image, whether XObject or inline.

    A CCITT image is reported additionally as ``Group4`` or ``Group3`` so tests
    can distinguish the two, whether the image survives as an XObject (its
    ``/DecodeParms`` carries ``/K``) or is inlined into the content stream
    (shortened filter ``/F/CCF``).
    """
    codecs: list[str] = []
    with pikepdf.open(path) as pdf:
        for page in pdf.pages:
            for key in page.images:
                stream = cast("pikepdf.Stream", page.images[key])
                img = pikepdf.PdfImage(stream)
                filters = [str(f) for f in img.filters]
                codecs.extend(filters)
                if "/CCITTFaxDecode" in filters:
                    codecs.append(_ccitt_group(stream.get("/DecodeParms")))
            content = _page_content(page)
            if b"/F/CCF" in content:
                codecs.append("/CCITTFaxDecode")
                codecs.append(
                    "Group4" if re.search(rb"/K\s*-1\b", content) else "Group3"
                )
    return codecs


def _page_image_xobjects(page: pikepdf.Page) -> list[pikepdf.Stream]:
    """Return the image XObject streams referenced by a page."""
    resources = page.obj.get("/Resources")
    xobjects = resources.get("/XObject")
    return [
        obj
        for _key, obj in xobjects.items()
        if isinstance(obj, pikepdf.Stream)
        and obj.get("/Subtype") == pikepdf.Name("/Image")
    ]


def get_raw_image_streams(path: str) -> list[bytes]:
    """Return the raw (undecoded) bytes of each XObject image in a PDF."""
    with pikepdf.open(path) as pdf:
        return [
            bytes(obj.read_raw_bytes())
            for page in pdf.pages
            for obj in _page_image_xobjects(page)
        ]


def _strip_trailing_eoi(data: bytes) -> bytes:
    """Drop redundant JPEG end-of-image markers some writers append."""
    while data.endswith(b"\xff\xd9"):
        data = data[:-2]
    return data


def test_has_locale() -> None:
    """Test has_locale function."""
    assert has_locale("C") is True
    assert has_locale("non-existent-locale") is False


def test_ccitt_group_from_decodeparms() -> None:
    """Group 4 is detected from a bare or array-wrapped DecodeParms /K."""
    assert _ccitt_group(None) == "Group3"
    assert _ccitt_group(pikepdf.Dictionary(K=0)) == "Group3"
    assert _ccitt_group(pikepdf.Dictionary(K=-1)) == "Group4"
    assert _ccitt_group(pikepdf.Array([pikepdf.Dictionary(K=-1)])) == "Group4"
    assert _ccitt_group(pikepdf.Array([pikepdf.Dictionary(K=0)])) == "Group3"
    assert _ccitt_group(pikepdf.Name("/NotADictionary")) == "Group3"


def test_form_xobject_streams_skip_non_forms_and_cycles() -> None:
    """Only Form XObjects are yielded, once, including nested resources."""
    pdf = pikepdf.new()
    form = pdf.make_stream(b"q 1 0 0 1 0 0 cm Q")
    form["/Subtype"] = pikepdf.Name("/Form")
    image = pdf.make_stream(b"\x00")
    image["/Subtype"] = pikepdf.Name("/Image")
    form["/Resources"] = pikepdf.Dictionary(
        XObject=pikepdf.Dictionary(
            Image=image,
            NotAStream=pikepdf.Name("/Foo"),
            Again=form,
        )
    )
    resources = pikepdf.Dictionary(
        XObject=pikepdf.Dictionary(Form=form, NotADictionary=pikepdf.Name("/Foo"))
    )

    assert list(_form_xobject_streams(resources, set())) == [b"q 1 0 0 1 0 0 cm Q"]
    assert list(_form_xobject_streams(pikepdf.Name("/NoResources"), set())) == []
    assert list(_form_xobject_streams(pikepdf.Dictionary(), set())) == []
    assert (
        list(
            _form_xobject_streams(
                pikepdf.Dictionary(XObject=pikepdf.Name("/No")), set()
            )
        )
        == []
    )


def test_has_rotated_text_ignores_non_text_content() -> None:
    """A content stream without BT is not treated as rotated text."""
    assert not _has_rotated_text(b"0 0 m 10 10 l S")


def test_get_pdf_image_codecs_ccitt_xobject(tmp_path: pathlib.Path) -> None:
    """A CCITT Group 4 XObject is reported from its DecodeParms.

    This covers the XObject form independently of whether ocrmypdf inlines the
    bilevel image in the content stream.
    """
    pdf = pikepdf.new()
    page = pdf.add_blank_page(page_size=(72, 72))
    page.obj["/Contents"] = pdf.make_stream(b"")
    image = pdf.make_stream(b"\x00")
    image["/Type"] = pikepdf.Name("/XObject")
    image["/Subtype"] = pikepdf.Name("/Image")
    image["/Width"] = 1
    image["/Height"] = 1
    image["/BitsPerComponent"] = 1
    image["/ColorSpace"] = pikepdf.Name("/DeviceGray")
    image["/Filter"] = pikepdf.Name("/CCITTFaxDecode")
    image["/DecodeParms"] = pikepdf.Dictionary(Columns=1, Rows=1, K=-1, BlackIs1=True)
    page.obj["/Resources"] = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=image))
    path = tmp_path / "ccitt.pdf"
    pdf.save(str(path))
    assert get_pdf_image_codecs(str(path)) == ["/CCITTFaxDecode", "Group4"]


def test_do_save_pdf(rose_pnm: str, temp_db: object, temp_pdf: object) -> None:
    """Test writing basic PDF."""
    thread = DocThread(db=temp_db.name)
    thread._write_tid = threading.get_native_id()
    with tempfile.TemporaryDirectory() as tdir:
        _number, _thumb, page_id = thread.add_page(
            Page(
                filename=rose_pnm,
                dir=tdir,
                delete=True,
                format="Portable anymap",
                resolution=(POINTS_PER_INCH, POINTS_PER_INCH, "PixelsPerInch"),
                width=70,
                height=46,
            ),
        )
        options = {
            "dir": tdir,
            "path": temp_pdf.name,
            "list_of_pages": [page_id],
            "options": {},
        }
        request = Request("save_pdf", (options,), queue.Queue())
        thread.do_save_pdf(request)
        width, height = get_page_size(temp_pdf.name)
        assert (width, height) == pytest.approx((70, 46), 0.1), "valid PDF created"


def test_save_pdf(
    rose_pnm: str,
    temp_db: object,
    temp_pdf: object,
    clean_up_files: Callable[[list[str]], None],
) -> None:
    """Test writing basic PDF."""
    slist = Document(db=temp_db.name)

    asserts = 0

    def import_files_started_cb(response: object) -> None:
        nonlocal asserts
        assert response.request.process in ["get_file_info", "import_file"]
        asserts += 1

    def import_files_finished_cb(_response: object) -> None:
        nonlocal asserts
        assert not slist.thread.pages_saved(), "pages not tagged as saved"
        asserts += 1
        mlp.quit()

    slist.import_files(
        paths=[rose_pnm],
        started_callback=import_files_started_cb,
        finished_callback=import_files_finished_cb,
    )
    mlp = safe_mainloop(5000)
    mlp.run()

    def save_pdf_started_cb(result: object) -> None:
        nonlocal asserts
        assert result.request.process == "save_pdf", "save_pdf"
        asserts += 1

    def save_pdf_finished_cb(_result: object) -> None:
        nonlocal asserts
        width, height = get_page_size(temp_pdf.name)
        assert (width, height) == pytest.approx((70, 46), 0.1), "valid PDF created"
        assert slist.thread.pages_saved(), "pages tagged as saved"
        asserts += 1
        mlp.quit()

    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        options={
            "post_save_hook": "pdftoppm %i test",
        },
        started_callback=save_pdf_started_cb,
        finished_callback=save_pdf_finished_cb,
    )
    mlp = safe_mainloop(5000)
    mlp.run()
    assert asserts == 5, "ran all callbacks"

    img = Image.open("test-1.ppm")
    assert img.format == "PPM", "ran post-save hook on pdf"
    assert img.size == (146, 96), "post-save hook dimensions"

    #########################

    clean_up_files(["test-1.ppm"])


@pytest.mark.skipif(
    not has_locale("de_DE.utf8"), reason="Locale de_DE.utf8 not available"
)
def test_save_pdf_with_locale(
    rose_pnm: str,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test with non-English locale."""
    locale.setlocale(locale.LC_CTYPE, "de_DE.utf8")

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=mlp.quit,
    )
    mlp.run()

    width, height = get_page_size(temp_pdf.name)
    assert (width, height) == pytest.approx((70, 46), 0.1), "valid PDF created"


def test_save_pdf_with_error(
    rose_pnm: str,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test saving a PDF and triggering an error."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as dirname:
        slist = Document(dir=dirname)
        asserts = 0

        import_in_mainloop(slist, [rose_pnm])

        # inject error before save_pdf
        pathlib.Path(dirname).chmod(0o500)  # no write access

        def error_callback1(response: Response) -> None:
            """No write access."""
            assert "unable to write to" in (response.status or "")
            nonlocal asserts
            asserts += 1
            mlp.quit()

        mlp = safe_mainloop(5000)
        slist.save_pdf(
            path=temp_pdf.name,
            list_of_pages=[slist.data[0][2]],
            error_callback=error_callback1,
        )
        mlp.run()

        def error_callback2(_response: Response) -> None:
            assert True, "save_pdf caught error injected in queue"
            pathlib.Path(dirname).chmod(0o700)  # allow write access
            nonlocal asserts
            asserts += 1
            mlp.quit()

        mlp = safe_mainloop(5000)
        slist.save_pdf(
            path=temp_pdf.name,
            list_of_pages=[slist.data[0][2]],
            error_callback=error_callback2,
        )
        mlp.run()

        assert asserts == 2, "ran all callbacks"


def test_save_pdf_different_resolutions(
    temp_png: object,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test saving a PDF with different resolutions in the height and width directions."""
    # Create test image
    subprocess.run(
        [config.CONVERT_COMMAND, "rose:", "-density", "100x200", temp_png.name],
        check=True,
    )

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_png.name])

    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    width, height = get_page_size(temp_pdf.name)
    assert (width, height) == pytest.approx((50.4, 16.56), 0.1), "valid PDF created"


@pytest.mark.skipif(shutil.which("qpdf") is None, reason="qpdf not found")
def test_save_encrypted_pdf(
    rose_jpg: str,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test saving an encrypted PDF."""
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_jpg])
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        options={"user-password": "123"},
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    with pytest.raises(pikepdf.PasswordError):
        pikepdf.open(temp_pdf.name)


def test_save_pdf_with_hocr(
    import_in_mainloop: Callable[[object, list[str]], None],
    set_text_in_mainloop: Callable[[object, str, str], None],
    temp_db: object,
    temp_pdf: object,
    temp_png: object,
    get_page_sync: Callable[..., object],
) -> None:
    """Test writing PDF with text layer from hocr."""
    subprocess.run(
        [
            config.CONVERT_COMMAND,
            "label:The quick brown fox",
            "-alpha",
            "Off",
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
            "-border",
            "20x10",
            temp_png.name,
        ],
        check=True,
    )
    img = Image.open(temp_png.name)
    width, height = img.size

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_png.name])

    hocr = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title></title>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>
  <meta name='ocr-system' content='tesseract 5.3.4' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word ocrp_wconf'/>
 </head>
 <body>
  <div class='ocr_page' id='page_1' title='bbox 0 0 136 38; ppageno 0; scan_res 300 300'>
   <div class='ocr_carea' id='block_1_1' title="bbox 20 13 115 26">
    <p class='ocr_par' id='par_1_1' lang='eng' title="bbox 20 13 115 26">
     <span class='ocr_line' id='line_1_1' title="bbox 20 13 115 26; baseline 0 -3; x_size 21.25; x_descenders 5.5; x_ascenders 5.25">
      <span class='ocrx_word' id='word_1_1' title='bbox 16 4 36 33; x_wconf 66'>The</span>
      <span class='ocrx_word' id='word_1_2' title='bbox 40 13 115 26; x_wconf 17'>quick brown</span>
      <span class='ocrx_word' id='word_1_3' title='bbox 100 4 118 33; x_wconf 65'>fox</span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    page = get_page_sync(slist.thread, id=1)
    page.import_hocr(hocr)
    set_text_in_mainloop(slist, cast("str", cast("object", 1)), page.text_layer)

    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()
    subprocess.run(["cp", temp_pdf.name, "fox.pdf"], check=True)

    capture = subprocess.check_output(["pdftotext", temp_pdf.name, "-"], text=True)
    assert re.search(  # some tesseract installations find an extra "r"
        r"Thr?e.*quick.*brow[mn].*f", capture, re.DOTALL
    ), "PDF with expected text"

    import_in_mainloop(slist, [temp_pdf.name])

    # Because we cannot reproduce the exact typeface used
    # in the original, we cannot expect to be able to
    # round-trip the text layer. Here, at least we can check
    # that we have scaled the page size correctly.
    page = get_page_sync(slist.thread, id=slist.data[1][2])
    regex = re.search(r"bbox\s0\s0\s(\d+)\s(\d+)", page.export_hocr())
    assert regex is not None, "hOCR contains a page bbox"
    page_width, page_height = int(regex.group(1)), int(regex.group(2))
    assert abs(page_width - width) < 2, "imported page width correct"
    assert abs(page_height - height) < 2, "imported page height correct"


def test_save_pdf_with_rotated_text_layer(
    temp_png: object,
    temp_pdf: object,
    temp_db: object,
    tmp_path: pathlib.Path,
    import_in_mainloop: Callable[[object, list[str]], None],
    set_text_in_mainloop: Callable[[object, str, str], None],
) -> None:
    """A rotated word is rendered rotated in the saved PDF text layer."""
    Image.new("L", (200, 120), 255).save(temp_png.name)
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [temp_png.name])
    page_id = cast("str", slist.data[0][2])

    horizontal = (
        '[{"type": "page", "bbox": [0, 0, 200, 120], "depth": 0}, '
        '{"type": "carea", "bbox": [10, 10, 190, 110], "depth": 1}, '
        '{"type": "para", "bbox": [10, 10, 190, 110], "depth": 2}, '
        '{"type": "line", "bbox": [20, 30, 100, 60], "depth": 3}, '
        '{"type": "word", "bbox": [20, 30, 100, 60], "text": "FLAT", '
        '"depth": 4}]'
    )
    set_text_in_mainloop(slist, page_id, horizontal)
    horizontal_pdf = tmp_path / "horizontal.pdf"
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=str(horizontal_pdf),
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    with pikepdf.open(horizontal_pdf) as pdf:
        streams = _page_content_streams(pdf.pages[0])
    assert not any(_has_rotated_text(content) for content in streams), (
        "horizontal control is unrotated"
    )

    rotated = (
        '[{"type": "page", "bbox": [0, 0, 200, 120], "depth": 0}, '
        '{"type": "carea", "bbox": [10, 10, 190, 110], "depth": 1}, '
        '{"type": "para", "bbox": [10, 10, 190, 110], "depth": 2}, '
        '{"type": "line", "bbox": [20, 30, 100, 60], "depth": 3}, '
        '{"type": "word", "bbox": [20, 30, 100, 60], "text": "FLAT", '
        '"depth": 4}, '
        '{"type": "word", "bbox": [120, 10, 160, 100], "text": "UP", '
        '"textangle": 90, "depth": 1}]'
    )
    set_text_in_mainloop(slist, page_id, rotated)
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    with pikepdf.open(temp_pdf.name) as pdf:
        streams = _page_content_streams(pdf.pages[0])
    assert any(_has_rotated_text(content) for content in streams), (
        "rotated word has a rotated text transform"
    )

    extracted = subprocess.check_output(["pdftotext", temp_pdf.name, "-"], text=True)
    assert "FLAT" in extracted, "horizontal text remains extractable"
    assert "UP" in extracted, "rotated text remains extractable"


@pytest.mark.xfail(
    reason="ocrmypdf GlyphlessFont + PDF/A conversion mangles non-ASCII text extraction"
)
def test_save_pdf_with_utf8(
    rose_pnm: str,
    temp_pdf: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    set_text_in_mainloop: Callable[[object, str, str], None],
) -> None:
    """Test writing PDF with utf8 in text layer."""
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    set_text_in_mainloop(
        slist,
        cast("str", cast("object", 1)),
        '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
        '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
        '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
        '{"bbox": [1, 14, 20, 48], "type": "word", "text": "пени", "depth": 3}, '
        '{"bbox": [21, 14, 50, 48], "type": "word", "text": "способствовала", "depth": 3}, '
        '{"bbox": [51, 14, 77, 48], "type": "word", "text": "сохранению", "depth": 3}]',
    )

    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    out = subprocess.check_output(["pdftotext", temp_pdf.name, "-"], text=True)
    assert re.search(r"пени\s*способствовала\s*сохранению", out) is not None, (
        "PDF with expected text"
    )


def test_save_pdf_with_1bpp(
    temp_pbm: object,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    clean_up_files: Callable[[list[str]], None],
) -> None:
    """Test writing PDF with a 1bpp image."""
    subprocess.run(
        [config.CONVERT_COMMAND, "magick:netscape", temp_pbm.name], check=True
    )

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pbm.name])

    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    subprocess.run(["pdfimages", temp_pdf.name, "x"], check=True)
    img = Image.open(next(pathlib.Path().glob("x-000.p*m")))
    assert img.mode == "1", "PDF with 1bpp created"
    assert "/CCITTFaxDecode" in get_pdf_image_codecs(temp_pdf.name), (
        "auto-selected bilevel page embedded with Group 4"
    )
    assert "Group4" in get_pdf_image_codecs(temp_pdf.name), "CCITT Group 4, not G3"

    #########################

    clean_up_files(cast("list[str]", pathlib.Path().glob("x-000.p*m")))


def test_save_pdf_g4(
    rose_png: str,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    clean_up_files: Callable[[list[str]], None],
) -> None:
    """Test writing PDF with group 4 compression."""
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_png])
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        options={
            "compression": "g4",
        },
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    subprocess.run(["pdfimages", temp_pdf.name, "x"], check=True)
    img = Image.open(next(pathlib.Path().glob("x-000.p*m")))
    assert img.mode == "1", "PDF with 1bpp created from 8-bit image"
    assert "/CCITTFaxDecode" in get_pdf_image_codecs(temp_pdf.name), (
        "explicit Group 4 page embedded with CCITT Group 4"
    )
    assert "Group4" in get_pdf_image_codecs(temp_pdf.name), "CCITT Group 4, not G3"

    #########################

    clean_up_files(cast("list[str]", pathlib.Path().glob("x-000.p*m")))


def test_save_pdf_g4_alpha(
    temp_tif: object,
    temp_png: object,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test writing PDF with group 4 compression."""
    subprocess.run(
        [
            config.CONVERT_COMMAND,
            "rose:",
            "-define",
            "tiff:rows-per-strip=1",
            "-compress",
            "group4",
            temp_tif.name,
        ],
        check=True,
    )

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_tif.name])

    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        options={
            "compression": "g4",
        },
        finished_callback=lambda _response: mlp.quit(),
    )
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
            f"-sOutputFile={temp_png.name}",
            temp_pdf.name,
        ],
        check=True,
    )
    example = subprocess.check_output(
        [
            config.CONVERT_COMMAND,
            temp_png.name,
            "-depth",
            "1",
            "-alpha",
            "off",
            "txt:-",
        ],
        text=True,
    )
    expected = subprocess.check_output(
        [
            config.CONVERT_COMMAND,
            temp_tif.name,
            "-depth",
            "1",
            "-alpha",
            "off",
            "txt:-",
        ],
        text=True,
    )
    assert example == expected, "valid G4 PDF created from multi-strip TIFF"


def test_save_pdf_auto_colour_is_jpeg(
    rose_png: str,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Automatic compression embeds a continuous-tone page as JPEG."""
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_png])
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        options={"quality": 75},
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    assert "/DCTDecode" in get_pdf_image_codecs(temp_pdf.name), "colour page as JPEG"


def test_save_pdf_low_colour_depth_grayscale_is_flate(
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Automatic compression embeds a posterised grayscale page as Flate."""
    with tempfile.NamedTemporaryFile(suffix=".tif") as src:
        image = Image.new("L", (64, 64))
        image.putdata([(i % 8) * 36 for i in range(64 * 64)])
        image.save(src.name)
        slist = Document(db=temp_db.name)
        import_in_mainloop(slist, [src.name])
        mlp = safe_mainloop(5000)
        slist.save_pdf(
            path=temp_pdf.name,
            list_of_pages=[slist.data[0][2]],
            finished_callback=lambda _response: mlp.quit(),
        )
        mlp.run()

    codecs = get_pdf_image_codecs(temp_pdf.name)
    assert "/FlateDecode" in codecs, "posterised page written losslessly"
    assert "/DCTDecode" not in codecs, "posterised page not JPEG"


def test_save_pdf_quality_shrinks_jpeg_stream(
    rose_png: str,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """A lower JPEG quality produces a smaller embedded image stream."""
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_png])
    sizes = {}
    for quality in (20, 95):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as out:
            mlp = safe_mainloop(5000)
            slist.save_pdf(
                path=out.name,
                list_of_pages=[slist.data[0][2]],
                options={"quality": quality},
                finished_callback=lambda _response, mlp=mlp: mlp.quit(),
            )
            mlp.run()
            streams = get_raw_image_streams(out.name)
            assert streams, "PDF contains an image"
            sizes[quality] = sum(len(stream) for stream in streams)
    assert sizes[20] < sizes[95], "lower quality stream is smaller"


@pytest.mark.skipif(
    not bool(features.check("jpg_2000")),
    reason="Pillow built without JPEG 2000 support",
)
def test_save_pdf_jp2(
    rose_png: str,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    clean_up_files: Callable[[list[str]], None],
) -> None:
    """An explicit jp2 save embeds a continuous-tone page as JPEG 2000."""
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_png])
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        options={"compression": "jp2", "quality": 75},
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    subprocess.run(["pdfimages", "-all", temp_pdf.name, "x"], check=True)
    with Image.open("x-000.jp2") as img:
        assert img.size == (70, 46), "JPEG 2000 image extracted"
    codecs = get_pdf_image_codecs(temp_pdf.name)
    assert "/JPXDecode" in codecs, "page as JPEG 2000"
    assert "/DCTDecode" not in codecs, "not JPEG"

    clean_up_files(["x-000.jp2"])


@pytest.mark.skipif(
    not bool(features.check("jpg_2000")),
    reason="Pillow built without JPEG 2000 support",
)
def test_save_pdf_jp2_quality_shrinks_stream(
    rose_png: str,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """A lower jp2 quality produces a smaller embedded image stream."""
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_png])
    sizes = {}
    for quality in (20, 95):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as out:
            mlp = safe_mainloop(5000)
            slist.save_pdf(
                path=out.name,
                list_of_pages=[slist.data[0][2]],
                options={"compression": "jp2", "quality": quality},
                finished_callback=lambda _response, mlp=mlp: mlp.quit(),
            )
            mlp.run()
            streams = get_raw_image_streams(out.name)
            assert streams, "PDF contains an image"
            sizes[quality] = sum(len(stream) for stream in streams)
    assert sizes[20] < sizes[95], "lower quality stream is smaller"


def test_save_pdf_jp2_bilevel_is_group4(
    temp_pbm: object,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """An explicit jp2 save of a bilevel page stays CCITT Group 4."""
    subprocess.run(
        [config.CONVERT_COMMAND, "magick:netscape", temp_pbm.name], check=True
    )
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [temp_pbm.name])
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        options={"compression": "jp2", "quality": 75},
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    codecs = get_pdf_image_codecs(temp_pdf.name)
    assert "/CCITTFaxDecode" in codecs, "bilevel page as Group 4"
    assert "Group4" in codecs, "CCITT Group 4, not G3"
    assert "/JPXDecode" not in codecs, "bilevel page not JPEG 2000"


def test_save_pdf_jp2_alpha_is_flate(
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """An explicit jp2 save of an image with alpha stays lossless Flate."""
    with tempfile.NamedTemporaryFile(suffix=".png") as alpha:
        subprocess.run(
            [config.CONVERT_COMMAND, "rose:", "-alpha", "set", alpha.name], check=True
        )
        slist = Document(db=temp_db.name)
        import_in_mainloop(slist, [alpha.name])
        mlp = safe_mainloop(5000)
        slist.save_pdf(
            path=temp_pdf.name,
            list_of_pages=[slist.data[0][2]],
            options={"compression": "jp2", "quality": 75},
            finished_callback=lambda _response: mlp.quit(),
        )
        mlp.run()

    codecs = get_pdf_image_codecs(temp_pdf.name)
    assert "/JPXDecode" not in codecs, "alpha page not JPEG 2000"


def test_save_pdf_flate_stays_flate_through_pdfa(
    rose_png: str,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """An explicit Flate save survives the PDF/A conversion as Flate."""
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_png])
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        options={"compression": "png"},
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    codecs = get_pdf_image_codecs(temp_pdf.name)
    assert "/FlateDecode" in codecs, "lossless page stays Flate through PDF/A"
    assert "/DCTDecode" not in codecs, "lossless page not transcoded to JPEG"


def test_save_pdf_jpeg_stays_jpeg_through_pdfa(
    rose_jpg: str,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """An explicit JPEG save survives the PDF/A conversion as JPEG."""
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_jpg])
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        options={"compression": "jpg"},
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    codecs = get_pdf_image_codecs(temp_pdf.name)
    assert "/DCTDecode" in codecs, "JPEG page stays JPEG through PDF/A"
    assert "/FlateDecode" not in codecs, "JPEG page not re-encoded losslessly"


@pytest.mark.skipif(not jbig2_available(), reason="jbig2 encoder not installed")
def test_save_pdf_jb2(
    temp_pbm: object,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """An explicit jb2 save embeds a bilevel page as lossless JBIG2."""
    _write_large_bilevel(temp_pbm.name)
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [temp_pbm.name])
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        options={"compression": "jb2"},
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    codecs = get_pdf_image_codecs(temp_pdf.name)
    assert "/JBIG2Decode" in codecs, "bilevel page embedded with JBIG2"
    assert "/CCITTFaxDecode" not in codecs, "not Group 4"


@pytest.mark.skipif(not jbig2_available(), reason="jbig2 encoder not installed")
def test_save_pdf_jb2_smaller_than_g4(
    temp_pbm: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """A bilevel page saved as JBIG2 is smaller than the same page as Group 4."""
    _write_large_bilevel(temp_pbm.name)
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [temp_pbm.name])
    sizes = {}
    for compression in ("g4", "jb2"):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as out:
            mlp = safe_mainloop(5000)
            slist.save_pdf(
                path=out.name,
                list_of_pages=[slist.data[0][2]],
                options={"compression": compression},
                finished_callback=lambda _response, mlp=mlp: mlp.quit(),
            )
            mlp.run()
            streams = get_raw_image_streams(out.name)
            assert streams, "PDF contains an image"
            sizes[compression] = sum(len(stream) for stream in streams)
    assert sizes["jb2"] < sizes["g4"], "JBIG2 stream smaller than Group 4"


def test_save_pdf_jb2_without_encoder_falls_back_to_g4(
    temp_pbm: object,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A jb2 request without the encoder degrades to Group 4, not an error."""
    monkeypatch.setattr("scantpaper.savethread.jbig2_available", lambda: False)
    _write_large_bilevel(temp_pbm.name)
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [temp_pbm.name])
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        options={"compression": "jb2"},
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    codecs = get_pdf_image_codecs(temp_pdf.name)
    assert "/CCITTFaxDecode" in codecs, "fell back to Group 4"
    assert "Group4" in codecs, "CCITT Group 4, not G3"
    assert "/JBIG2Decode" not in codecs, "no JBIG2 without the encoder"


def test_save_pdf_auto_bilevel_prefers_g4_by_default(
    temp_pbm: object,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Under auto, the default bilevel preference keeps Group 4."""
    _write_large_bilevel(temp_pbm.name)
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [temp_pbm.name])
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        options={"bilevel compression": "g4"},
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    codecs = get_pdf_image_codecs(temp_pdf.name)
    assert "/CCITTFaxDecode" in codecs, "Group 4 under auto with g4 preference"
    assert "/JBIG2Decode" not in codecs, "no JBIG2 under auto with g4 preference"


@pytest.mark.skipif(not jbig2_available(), reason="jbig2 encoder not installed")
def test_save_pdf_auto_bilevel_jbig2_preference(
    temp_pbm: object,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Under auto, a jb2 preference embeds bilevel pages as JBIG2."""
    _write_large_bilevel(temp_pbm.name)
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [temp_pbm.name])
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        options={"bilevel compression": "jb2"},
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    codecs = get_pdf_image_codecs(temp_pdf.name)
    assert "/JBIG2Decode" in codecs, "JBIG2 under auto with jb2 preference"


def test_save_pdf_auto_bilevel_jbig2_preference_without_encoder(
    temp_pbm: object,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Under auto, a jb2 preference without the encoder falls back to Group 4."""
    monkeypatch.setattr("scantpaper.savethread.jbig2_available", lambda: False)
    _write_large_bilevel(temp_pbm.name)
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [temp_pbm.name])
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        options={"bilevel compression": "jb2"},
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    codecs = get_pdf_image_codecs(temp_pdf.name)
    assert "/CCITTFaxDecode" in codecs, "fell back to Group 4 without the encoder"
    assert "Group4" in codecs, "CCITT Group 4, not G3"
    assert "/JBIG2Decode" not in codecs, "no JBIG2 without the encoder"


@pytest.mark.skipif(not jbig2_available(), reason="jbig2 encoder not installed")
def test_save_pdf_auto_jbig2_preference_keeps_jpeg(
    rose_png: str,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """The bilevel preference never switches continuous-tone pages from JPEG."""
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_png])
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        options={"bilevel compression": "jb2", "quality": 75},
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    codecs = get_pdf_image_codecs(temp_pdf.name)
    assert "/DCTDecode" in codecs, "continuous-tone page stays JPEG"
    assert "/JBIG2Decode" not in codecs, "continuous-tone page not JBIG2"


def test_save_pdf_auto_imported_jpeg_verbatim(
    rose_jpg: str,
    temp_db: object,
    temp_pdf: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """An unmodified imported JPEG is embedded without re-encoding under auto."""
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_jpg])
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    original = pathlib.Path(rose_jpg).read_bytes()
    streams = get_raw_image_streams(temp_pdf.name)
    assert len(streams) == 1, "one embedded image stream"
    assert _strip_trailing_eoi(streams[0]) == _strip_trailing_eoi(original), (
        "original JPEG bytes embedded verbatim (not re-encoded)"
    )


def test_save_pdf_with_metadata(
    rose_pnm: str,
    temp_pdf: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test writing PDF with metadata."""
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    metadata = {
        "datetime": datetime.datetime(2016, 2, 10, 0, 0, tzinfo=datetime.timezone.utc),
        "title": "metadata title",
        "subject": "",
    }
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        metadata=metadata,
        options={"set_timestamp": True},
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    with pikepdf.open(temp_pdf.name) as pdf:
        docinfo = pdf.docinfo or {}
        assert docinfo.get("/Title") == "metadata title", "metadata title in PDF"
        assert "/Subject" not in docinfo or docinfo["/Subject"] != "", (
            "don't add blank metadata"
        )
        creationdate = str(cast("dict[str, object]", docinfo).get("/CreationDate", ""))
        assert "20160210" in creationdate, "metadata CreationDate in PDF"
    stb = pathlib.Path(temp_pdf.name).stat()
    assert datetime.datetime.fromtimestamp(
        stb.st_mtime, tz=datetime.timezone.utc
    ) == datetime.datetime(2016, 2, 10, 0, 0, 0, tzinfo=datetime.timezone.utc), (
        "timestamp"
    )


def test_save_pdf_without_title_has_no_placeholder_title(
    rose_pnm: str,
    temp_pdf: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test writing PDF without title gets no placeholder title."""
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    metadata = {
        "datetime": datetime.datetime(2016, 2, 10, 0, 0, tzinfo=datetime.timezone.utc),
    }
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        metadata=metadata,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    with pikepdf.open(temp_pdf.name) as pdf:
        docinfo = pdf.docinfo or {}
        assert "/Title" not in docinfo, "no placeholder title in docinfo"
        with pdf.open_metadata() as md:
            assert "dc:title" not in md, "no placeholder title in XMP"
    pdfinfo = subprocess.run(
        ["pdfinfo", temp_pdf.name], capture_output=True, text=True, check=True
    )
    assert "Title:" not in pdfinfo.stdout, "no placeholder title in pdfinfo"


def test_save_pdf_with_title_retains_title_in_xmp(
    rose_pnm: str,
    temp_pdf: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test writing PDF with title retains it in docinfo and XMP."""
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    metadata = {
        "datetime": datetime.datetime(2016, 2, 10, 0, 0, tzinfo=datetime.timezone.utc),
        "title": "metadata title",
    }
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        metadata=metadata,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    with pikepdf.open(temp_pdf.name) as pdf:
        docinfo = pdf.docinfo or {}
        assert docinfo.get("/Title") == "metadata title", "metadata title in docinfo"
        with pdf.open_metadata() as md:
            assert md.get("dc:title") == "metadata title", "metadata title in XMP"


def test_save_pdf_creator_branded(
    rose_pnm: str,
    temp_pdf: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test writing PDF brands scantpaper as creator, keeping toolchain provenance."""
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    metadata = {
        "datetime": datetime.datetime(2016, 2, 10, 0, 0, tzinfo=datetime.timezone.utc),
    }
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        metadata=metadata,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    with pikepdf.open(temp_pdf.name) as pdf:
        docinfo = pdf.docinfo or {}
        creator = str(cast("dict[str, object]", docinfo).get("/Creator", ""))
        assert creator.startswith("scantpaper v"), "scantpaper first in Creator"
        assert "OCRmyPDF" in creator, "OCRmyPDF provenance retained"
        assert "Tesseract" in creator, "Tesseract provenance retained"
        producer = str(cast("dict[str, object]", docinfo).get("/Producer", ""))
        assert producer.startswith("pikepdf"), "producer untouched"
        with pdf.open_metadata() as md:
            assert md.get("xmp:CreatorTool") == creator, "XMP creator matches docinfo"
            assert str(md.get("pdf:Producer")).startswith("pikepdf"), (
                "XMP producer untouched"
            )
            assert md.get("pdfaid:part") is not None, "PDF/A identification kept"


def test_save_pdf_creator_branded_with_title(
    rose_pnm: str,
    temp_pdf: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test writing PDF with a title still brands scantpaper as creator."""
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    metadata = {
        "datetime": datetime.datetime(2016, 2, 10, 0, 0, tzinfo=datetime.timezone.utc),
        "title": "metadata title",
    }
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        metadata=metadata,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    with pikepdf.open(temp_pdf.name) as pdf:
        docinfo = pdf.docinfo or {}
        assert docinfo.get("/Title") == "metadata title", "user title kept"
        creator = str(cast("dict[str, object]", docinfo).get("/Creator", ""))
        assert creator.startswith("scantpaper v"), "branded despite user title"
        assert "OCRmyPDF" in creator, "toolchain provenance retained"
        with pdf.open_metadata() as md:
            assert md.get("dc:title") == "metadata title", "user title in XMP"
            assert md.get("xmp:CreatorTool") == creator, "XMP creator matches docinfo"
            assert md.get("pdfaid:part") is not None, "PDF/A identification kept"


def test_save_import_without_title_roundtrip(
    rose_pnm: str,
    temp_pdf: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test saving without title and re-importing yields no title."""
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    metadata = {
        "datetime": datetime.datetime(2016, 2, 10, 0, 0, tzinfo=datetime.timezone.utc),
    }
    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        metadata=metadata,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    asserts = 0

    def metadata_cb(response: object) -> None:
        assert "title" not in cast("dict[str, object]", response), (
            "no title in re-imported metadata"
        )
        nonlocal asserts
        asserts += 1

    slist2 = Document(db=temp_db.name)
    mlp2 = safe_mainloop()
    slist2.import_files(
        paths=[temp_pdf.name],
        metadata_callback=metadata_cb,
        finished_callback=lambda _response: mlp2.quit(),
    )
    mlp2.run()

    assert asserts == 1, "metadata callback ran"


def test_save_pdf_with_old_metadata(
    rose_pnm: str,
    temp_pdf: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test writing PDF with old metadata."""
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    metadata = {
        "datetime": datetime.datetime(1966, 2, 10, 0, 0, tzinfo=datetime.timezone.utc),
        "title": "metadata title",
    }

    called = False

    def error_callback(_result: object) -> None:
        nonlocal called
        called = True
        mlp.quit()

    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        metadata=metadata,
        options={"set_timestamp": True},
        finished_callback=lambda _response: mlp.quit(),
        error_callback=error_callback,
    )
    mlp.run()

    assert called, "caught errors setting timestamp"

    with pikepdf.open(temp_pdf.name) as pdf:
        docinfo = pdf.docinfo or {}
        assert docinfo.get("/Title") == "metadata title", "metadata title in PDF"
        creationdate = str(cast("dict[str, object]", docinfo).get("/CreationDate", ""))
        assert "19660210" in creationdate, "metadata CreationDate in PDF"


def test_save_pdf_with_downsample(
    temp_png: object,
    temp_pdf: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    clean_up_files: Callable[[list[str]], None],
) -> None:
    """Test writing PDF with downsampled image."""
    subprocess.run(
        [
            config.CONVERT_COMMAND,
            "-density",
            "300",
            "label:The quick brown fox",
            "-alpha",
            "Off",
            "-depth",
            "1",
            "-colorspace",
            "Gray",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            temp_png.name,
        ],
        check=True,
    )

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_png.name])

    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    with tempfile.NamedTemporaryFile(suffix=".pdf") as temp_pdf2:
        mlp = safe_mainloop(5000)
        slist.save_pdf(
            path=temp_pdf2.name,
            list_of_pages=[slist.data[0][2]],
            options={
                "downsample": True,
                "downsample dpi": 150,
            },
            finished_callback=lambda _response: mlp.quit(),
        )
        mlp.run()

        assert (
            pathlib.Path(temp_pdf.name).stat().st_size
            > pathlib.Path(temp_pdf2.name).stat().st_size
        ), "downsampled PDF smaller than original"

        subprocess.run(["pdfimages", temp_pdf2.name, "x"], check=True)
        img = Image.open("x-000.pbm")
        assert img.mode == "1", "downsampled"
        assert img.size[0] > 0, "downsampled dimensions"
        assert img.size[1] > 0, "downsampled dimensions"

    clean_up_files(["x-000.pbm"])


def test_cancel_save_pdf(
    rose_pnm: str,
    temp_pdf: object,
    temp_db: object,
    temp_jpg: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test writing PDF with downsampled image."""
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    finished_callback = MagicMock()
    mlp = safe_mainloop(5000)
    called = False

    def cancelled_callback(_response: object) -> None:
        nonlocal called
        called = True
        mlp.quit()

    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=finished_callback,
    )
    slist.cancel(cancelled_callback)
    mlp.run()
    finished_callback.assert_not_called()

    slist.save_image(
        path=temp_jpg.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp = safe_mainloop(5000)
    mlp.run()

    img = Image.open(temp_jpg.name)
    assert img.format == "JPEG", (
        "can create a valid JPG after cancelling save PDF process"
    )


def test_import_pdf_without_text_and_resave(
    rose_png: str,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    clean_up_files: Callable[[list[str]], None],
) -> None:
    """Regression test for importing a PDF without a text layer.

    Re-saving it as a PDF would fail with: 'HocrTransform' object has no
    attribute 'width'.
    """
    # Create a PDF from a TIFF (no text layer)
    with (
        tempfile.NamedTemporaryFile(suffix=".pdf") as temp_pdf1,
        tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf2,
    ):
        temp_pdf1.write(img2pdf.convert(rose_png))
        temp_pdf1.flush()

        # Import the PDF without text layer
        slist = Document(db=temp_db.name)
        import_in_mainloop(slist, [temp_pdf1.name])

        assert len(slist.data) == 1, "imported 1 page"

        # Re-save it as PDF - this should not fail
        mlp = safe_mainloop(10000)

        slist.save_pdf(
            path=temp_pdf2.name,
            list_of_pages=[slist.data[0][2]],
            finished_callback=lambda _response: mlp.quit(),
        )
        mlp.run()

        # Verify the output PDF is valid
        width, height = get_page_size(temp_pdf2.name)
        assert width > 0, "valid PDF created"
        assert height > 0, "valid PDF created"

        clean_up_files([temp_pdf2.name])


def test_import_pdf_from_transparent_image_creates_one_page(
    temp_db: object, tmp_path: pathlib.Path
) -> None:
    """Regression test for issue #43: opening a transparent-image PDF.

    Import a single page, not an extra page for the alpha mask. The imported
    page must be the image composited over a white background.
    """
    image = Image.new("LA", (100, 50), (255, 0))
    image.putpixel((5, 5), (0, 255))
    image.putpixel((6, 5), (0, 128))
    png = str(tmp_path / "transparent.png")
    image.save(png)

    with tempfile.NamedTemporaryFile(suffix=".pdf") as temp_pdf:
        temp_pdf.write(img2pdf.convert(png))
        temp_pdf.flush()

        slist = Document(db=temp_db.name)
        error_cb = MagicMock()

        mlp = safe_mainloop(10000)

        slist.import_files(
            paths=[temp_pdf.name],
            error_callback=error_cb,
            finished_callback=lambda _response: mlp.quit(),
        )
        mlp.run()

        assert len(slist.data) == 1, "exactly one page imported"
        error_cb.assert_not_called()

        page = slist.thread.get_page(id=slist.data[0][2])
        imported = page.image_object.convert("L")
        assert imported.size == (100, 50)
        assert imported.getpixel((5, 5)) == 0, "opaque pixel stays black"
        assert imported.getpixel((6, 5)) == 127, (
            "half-transparent pixel blended with white"
        )
        assert imported.getpixel((0, 0)) == 255, "transparent pixel becomes white"


def test_save_pdf_with_empty_text_layer(
    rose_pnm: str, temp_db: object, temp_pdf: object
) -> None:
    """Regression test for saving a PDF with text_layer set to '[]'.

    An empty JSON array, as produced by tesseract when no text is found,
    would fail with: 'HocrTransform' object has no attribute 'width'.
    """
    thread = DocThread(db=temp_db.name)
    thread._write_tid = threading.get_native_id()
    with tempfile.TemporaryDirectory() as tdir:
        _number, _thumb, page_id = thread.add_page(
            Page(
                filename=rose_pnm,
                dir=tdir,
                delete=True,
                format="Portable anymap",
                resolution=(POINTS_PER_INCH, POINTS_PER_INCH, "PixelsPerInch"),
                width=70,
                height=46,
                text_layer="[]",
            ),
        )
        options = {
            "dir": tdir,
            "path": temp_pdf.name,
            "list_of_pages": [page_id],
            "options": {},
        }
        request = Request("save_pdf", (options,), queue.Queue())
        thread.do_save_pdf(request)
        width, height = get_page_size(temp_pdf.name)
        assert (width, height) == pytest.approx((70, 46), 0.1), "valid PDF created"
