"Test writing basic PDF"

import os
import re
import subprocess
import tempfile
import queue
from docthread import DocThread
from basethread import Request
from page import Page


def test_1():
    "Test writing basic PDF"

    # Create test image
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    thread = DocThread()
    tdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    options = {
        "dir": tdir.name,
        "path": "test.pdf",
        "list_of_pages": [
            Page(
                filename="test.pnm",
                dir=tdir.name,
                delete=True,
                format="Portable anymap",
                resolution=(70, 70, "PixelsPerInch"),
                width=70,
                height=46,
            )
        ],
        "options": {},
    }
    request = Request("save_pdf", (options,), queue.Queue())
    thread.do_save_pdf(request)
    capture = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
    assert re.search(r"Page size:\s+70 x 46 pts", capture), "valid PDF created"

    for fname in ["test.pnm", "test.pdf"]:
        if os.path.isfile(fname):
            os.remove(fname)
