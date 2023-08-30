"test saving PDF with text"

import os
import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "test saving PDF with text"
    # Create test image
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    # dir for temporary files
    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    mlp = GLib.MainLoop()
    slist.data[0][2].import_text("The quick brown fox")
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdftotext", "test.pdf", "-"], text=True)
    print(f"capture {capture}")
    assert (
        re.search(r"The quick brown fox", capture) is not None
    ), "PDF with expected text"

    #########################

    for fname in ["test.pnm", "test.pdf"]:
        if os.path.isfile(fname):
            os.remove(fname)
