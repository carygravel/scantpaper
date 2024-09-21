"Test prepending a page to a PDF with a space"

import os
import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test prepending a page to a PDF with a space"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)
    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    subprocess.run(["tiff2pdf", "-o", "te st.pdf", "test.tif"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.save_pdf(
        path="te st.pdf",
        list_of_pages=[slist.data[0][2].uuid],
        options={
            "prepend": "te st.pdf",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", "te st.pdf"], text=True)
    assert re.search(r"Pages:\s+2", capture) is not None, "PDF prepended"
    assert os.path.isfile("te st.pdf.bak"), "Backed up original"

    #########################

    clean_up_files(["test.pnm", "test.tif", "te st.pdf", "te st.pdf.bak"])
