"Test importing PDF"

import os
import re
import subprocess
import tempfile
import shutil
import pytest
from gi.repository import GLib
from document import Document


def test_1():
    "Test importing PDF"

    if shutil.which("pdfunite") is None:
        pytest.skip("Please install pdfunite (poppler utils) to enable test")

    subprocess.run(["convert", "rose:", "page1.tif"], check=True)
    subprocess.run(["tiff2pdf", "-o", "page1.pdf", "page1.tif"], check=True)
    content = b"""%PDF-1.4
1 0 obj
  << /Type /Catalog
      /Outlines 2 0 R
      /Pages 3 0 R
  >>
endobj

2 0 obj
  << /Type /Outlines
      /Count 0
  >>
endobj

3 0 obj
  << /Type /Pages
      /Kids [ 4 0 R ]
      /Count 1
  >>
endobj

4 0 obj
  << /Type /Page
      /Parent 3 0 R
      /MediaBox [ 0 0 612 792 ]
      /Contents 7 0 R
      /Resources 5 0 R
  >>
endobj

5 0 obj
  << /Font <</F1 6 0 R >> >>
endobj

6 0 obj
  << /Type /Font
      /Subtype /Type1
      /Name /F1
      /BaseFont /Courier
  >>
endobj

7 0 obj
  << /Length 62 >>
stream
  BT
    /F1 24 Tf
    100 100 Td
    ( Hello World ) Tj
  ET
endstream
endobj
xref
0 8
0000000000 65535 f 
0000000009 00000 n 
0000000091 00000 n 
0000000148 00000 n 
0000000224 00000 n 
0000000359 00000 n 
0000000404 00000 n 
0000000505 00000 n 
trailer
<</Size 8/Root 1 0 R>> 
startxref
618
%%EOF
"""
    with open("page2.pdf", "wb") as fhd:
        fhd.write(content)
    subprocess.run(["pdfunite", "page1.pdf", "page2.pdf", "test.pdf"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    mlp = GLib.MainLoop()

    asserts = 0

    def logger_cb(_page, _process, message):
        print(f"in logger_cb {_page} {_process} {message}")
        nonlocal asserts
        asserts += 1
        assert re.search(r"one image per page", message), "one image per page warning"

    slist.import_files(
        paths=["test.pdf"],
        logger_callback=logger_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"
    assert len(slist.data) == 1, "imported 1 pages"

    #########################

    for fname in ["page1.tif", "page1.pdf", "test2.pdf", "test.pdf"]:
        if os.path.isfile(fname):
            os.remove(fname)
