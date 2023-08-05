"Test with non-English locale"

import os
import re
import subprocess
import locale
import tempfile
from gi.repository import GLib
from document import Document


def test_1():
    "Test with non-English locale"
    locale.setlocale(locale.LC_NUMERIC, "de_DE.utf8")

    # Create test image
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    # dir for temporary files
    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    mlp = GLib.MainLoop()
    slist.import_files(paths=["test.pnm"], finished_callback=mlp.quit)
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf", list_of_pages=[slist.data[0][2]], finished_callback=mlp.quit
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
    assert (
        re.search(r"Page size:\s+70 x 46 pts", capture) is not None
    ), "valid PDF created"

    #########################

    for fname in ["test.pnm", "test.pdf"]:
        if os.path.isfile(fname):
            os.remove(fname)
