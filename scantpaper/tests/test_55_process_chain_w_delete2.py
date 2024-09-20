"Test error handling in process chain"

import os
import tempfile
import shutil
import pytest
from gi.repository import GLib
from document import Document


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
def test_1(rotated_qbfox_image):
    "Test error handling in process chain"

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with

    slist = Document()
    slist.set_dir(dirname.name)

    asserts = 0
    mlp = GLib.MainLoop()

    def started_callback(_response):
        slist.select(0)
        slist.delete_selection()

    def error_callback(_response):
        nonlocal asserts
        asserts += 1
        mlp.quit()

    def finished_callback(_response):
        nonlocal asserts
        asserts += 1
        mlp.quit()

    options = {
        "filename": rotated_qbfox_image,
        "to_png": True,
        "rotate": -90,
        "ocr": True,
        "resolution": 300,
        "delete": False,
        "dir": dirname.name,
        "engine": "tesseract",
        "language": "eng",
        "error_callback": error_callback,
        "finished_callback": finished_callback,
    }
    slist.import_scan(page=1, **options)
    slist.import_scan(page=2, started_callback=started_callback, **options)
    GLib.timeout_add(5000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts > 0, "Didn't hang waiting for deleted page"

    #########################

    os.remove(rotated_qbfox_image)
