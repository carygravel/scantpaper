"Test to_png in process chain"

import tempfile
import shutil
import re
import pytest
from gi.repository import GLib
from document import Document


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
def test_1(rotated_qbfox_image, clean_up_files):
    "Test to_png in process chain"

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with

    slist = Document()
    slist.set_dir(dirname.name)

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        asserts += 1

    mlp = GLib.MainLoop()
    slist.import_scan(
        filename=rotated_qbfox_image,
        page=1,
        to_png=True,
        rotate=-90,
        ocr=True,
        resolution=300,
        delete=True,
        dir=dirname.name,
        engine="tesseract",
        language="eng",
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(5000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert re.search(r"png$", slist.data[0][2].filename), "converted PNM to PNG"
    assert asserts == 4, "display callback called for import, rotate, to_png, tesseract"
    assert slist.data[0][2].resolution[0] == 300, "Resolution of imported image"

    hocr = slist.data[0][2].export_hocr()
    assert re.search(r"T[hn]e", hocr), 'Tesseract returned "The"'
    assert re.search(r"quick", hocr), 'Tesseract returned "quick"'
    assert re.search(r"brown", hocr), 'Tesseract returned "brown"'
    assert re.search(r"f(o|0)x", hocr), 'Tesseract returned "fox"'

    #########################

    clean_up_files([rotated_qbfox_image])
