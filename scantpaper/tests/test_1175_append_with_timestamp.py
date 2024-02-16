"Test appending a page to a PDF with a timestamp"

import os
import re
import subprocess
import tempfile
import datetime
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test appending a page to a PDF with a timestamp"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)
    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    subprocess.run(["tiff2pdf", "-o", "test.pdf", "test.tif"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2].uuid],
        metadata={"datetime": [2016, 2, 10, 0, 0, 0], "title": "metadata title"},
        options={
            "append": "test.pdf",
            "set_timestamp": True,
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
    assert re.search(r"Pages:\s+2", capture), "PDF appended"
    assert os.path.isfile("test.pdf.bak"), "Backed up original"
    stb = os.stat("test.pdf")
    assert datetime.datetime.utcfromtimestamp(stb.st_mtime) == datetime.datetime(
        2016, 2, 10, 0, 0, 0
    ), "timestamp"

    #########################

    for fname in ["test.pnm", "test.tif", "test.pdf", "test.pdf.bak"]:
        if os.path.isfile(fname):
            os.remove(fname)
