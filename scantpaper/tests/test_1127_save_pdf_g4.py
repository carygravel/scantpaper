"Test writing PDF with group 4 compression"

import re
import subprocess
import tempfile
import glob
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test writing PDF with group 4 compression"

    subprocess.run(["convert", "rose:", "test.png"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.png"])

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2].uuid],
        options={
            "compression": "g4",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    subprocess.run(["pdfimages", "test.pdf", "x"], check=True)
    out = subprocess.check_output(["identify", "x-000.p*m"], text=True)
    assert (
        re.search(r"1-bit Bilevel Gray", out) is not None
    ), "PDF with 1bpp created from 8-bit image"

    #########################

    clean_up_files(["test.png", "test.pdf"] + glob.glob("x-000.p*m"))
