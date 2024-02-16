"Test saving a djvu with text layer from HOCR"

import os
import re
import subprocess
import tempfile
import shutil
import codecs
import pytest
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test saving a djvu with text layer from HOCR"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    hocr = """<!DOCTYPE html
 PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN
 http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
 <head>
  <meta content="ocr_line ocr_page" name="ocr-capabilities"/>
  <meta content="en" name="ocr-langs"/>
  <meta content="Latn" name="ocr-scripts"/>
  <meta content="" name="ocr-microformats"/>
  <title>OCR Output</title>
 </head>
 <body>
  <div class="ocr_page" title="bbox 0 0 70 46>
   <p class="ocr_par">
    <span class="ocr_line" title="bbox 10 10 60 11">The quick — brown fox·</span>
   </p>
  </div>
 </body>
</html>
"""
    slist.data[0][2].import_hocr(hocr)
    slist.data[0][2].import_annotations(hocr)
    slist.save_djvu(
        path="test.djvu",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["djvutxt", "test.djvu"], text=True)
    assert re.search(r"The quick — brown fox", capture), "DjVu with expected text"

    capture = subprocess.check_output(
        ["djvused", "test.djvu", "-e", "select 1; print-ant"]
    )
    assert re.search(
        r"The quick — brown fox", codecs.escape_decode(capture)[0].decode("utf-8")
    ), "DjVu with expected annotation"

    #########################

    for fname in ["test.pnm", "test.djvu"]:
        if os.path.isfile(fname):
            os.remove(fname)
