"Test tesseract helper functions"

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import pytest
from gi.repository import GLib
from document import Document
from tesseract import languages, _iso639_1to3, locale_installed, get_tesseract_codes


def test_tesseract_code_conversions():
    "Test tesseract helper functions"

    assert languages(["eng", "deu", "chi-sim-vert"]) == {
        "chi-sim-vert": "Chinese - Simplified (vertical)",
        "eng": "English",
        "deu": "German",
    }, "test languages()"
    assert _iso639_1to3("en") == "eng", "_iso639_1to3 en"
    assert _iso639_1to3("C") == "eng", "_iso639_1to3 C"
    assert _iso639_1to3("zh") == "chi-sim", "_iso639_1to3 zh"
    assert locale_installed("en_GB", ["eng"]) == "", "language installed"
    assert re.search(
        r"install", locale_installed("de_DE", ["eng"])
    ), "language installable"
    assert re.search(
        r"developers", locale_installed("kw_KW", ["eng"])
    ), "language not installable"
    assert re.search(
        r"necessary", locale_installed("zz_ZZ", ["eng"])
    ), "language unknown"


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
def test_get_tesseract_codes():
    "test get_tesseract_codes()"
    assert isinstance(get_tesseract_codes(), list), "get_tesseract_codes() returns list"


def test_tesseract_in_thread(import_in_mainloop, clean_up_files):
    "Test importing PDF"

    args = [
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
    ]
    subprocess.run(args, check=True)

    slist = Document()

    import_in_mainloop(slist, ["test.png"])

    mlp = GLib.MainLoop()
    slist.tesseract(
        page=slist.data[0][2],
        language="eng",
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    page = slist.thread.get_page(number=1)
    hocr = page.export_hocr()
    assert re.search(r"T[hn]e", hocr), 'Tesseract returned "The"'
    assert re.search(r"quick", hocr), 'Tesseract returned "quick"'
    assert re.search(r"brown", hocr), 'Tesseract returned "brown"'
    assert re.search(r"f(o|0)x", hocr), 'Tesseract returned "fox"'

    #########################

    clean_up_files([Path(tempfile.gettempdir()) / "document.db", "test.png"])
