"Test importing DjVu"

import re
import subprocess
import tempfile
import shutil
import pytest
from gi.repository import GLib
from document import Document
from page import Page


def mock_import_djvu_txt(self, _text):
    "mock import_djvu_txt method to test error handling"
    raise ValueError("Error parsing djvu text")


def test_1(monkeypatch, clean_up_files):
    "Test importing DjVu"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "test.jpg"], check=True)
    subprocess.run(["c44", "test.jpg", "test.djvu"], check=True)

    # apply the monkeypatch for Page.import_djvu_txt to mock_import_djvu_txt
    monkeypatch.setattr(Page, "import_djvu_txt", mock_import_djvu_txt)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    mlp = GLib.MainLoop()

    asserts = 0

    def logger_cb(response):
        nonlocal asserts
        assert re.search(r"error", response.status), "error_cb"
        asserts += 1

    slist.import_files(
        paths=["test.djvu"],
        logger_callback=logger_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"
    capture = subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", slist.data[0][2].filename],
        text=True,
    )
    assert re.search(r"^TIFF", capture), "DjVu imported otherwise correctly"

    #########################

    clean_up_files(["test.jpg", "test.djvu"])
