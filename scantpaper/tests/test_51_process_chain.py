"Test process chain"

import subprocess
import tempfile
import shutil
import re
import pytest
from gi.repository import GLib
from document import Document
from unpaper import Unpaper


@pytest.mark.skipif(
    shutil.which("unpaper") is None or shutil.which("tesseract") is None,
    reason="requires unpaper and tesseract",
)
def test_1(clean_up_files):
    "Test process chain"

    unpaper = Unpaper()
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
            "-rotate",
            "-90",
            "test.pnm",
        ],
        check=True,
    )
    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with

    slist = Document()
    slist.set_dir(dirname.name)

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        assert True, "Triggered display callback"
        asserts += 1

    mlp = GLib.MainLoop()
    slist.import_scan(
        filename="test.pnm",
        page=1,
        rotate=-90,
        unpaper=unpaper,
        ocr=True,
        resolution=300,
        delete=True,
        dir=dirname.name,
        engine="tesseract",
        language="eng",
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        asserts == 4
    ), "display callback called for import, rotate, unpaper, tesseract"
    assert slist.data[0][2].resolution[0] == 300, "Resolution of imported image"

    hocr = slist.data[0][2].export_hocr()
    assert re.search(r"T[hn]e", hocr), 'Tesseract returned "The"'
    assert re.search(r"quick", hocr), 'Tesseract returned "quick"'
    assert re.search(r"brown", hocr), 'Tesseract returned "brown"'
    assert re.search(r"f(o|0)x", hocr), 'Tesseract returned "fox"'

    #########################

    clean_up_files(["test.pnm"])
