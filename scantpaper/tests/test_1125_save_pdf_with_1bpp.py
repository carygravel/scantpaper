"Test writing PDF with a 1bpp image"

import os
import re
import subprocess
import tempfile
import glob
import pytest
from gi.repository import GLib
from document import Document


@pytest.mark.skip(
    reason="until we move to fpdf or OCRmyPDF, or solve "
    "https://stackoverflow.com/questions/77202653/"
    "embed-1bpp-image-in-pdf-using-python-and-reportlab"
)
def test_1(import_in_mainloop):
    "Test writing PDF with a 1bpp image"

    subprocess.run(["convert", "magick:netscape", "test.pbm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

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
    assert re.search(r"1-bit Bilevel Gray", out) is not None, "PDF with 1bpp created"

    #########################

    for fname in ["test.pnm", "test.pdf"] + glob.glob("x-000.p*m"):
        if os.path.isfile(fname):
            os.remove(fname)
