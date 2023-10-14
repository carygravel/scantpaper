"Test writing multipage PDF with utf8"

import re
import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test writing multipage PDF with utf8"

    num = 3  # number of pages
    files = []
    for i in range(num):
        filename = f"{i+1}.pnm"
        subprocess.run(["convert", "rose:", filename], check=True)
        files.append(filename)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, files)

    pages = []
    for i in range(num):
        slist.data[i][2].import_text("hello world")
        pages.append(slist.data[i][2])

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=pages,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        len(
            re.findall(
                "Times-Roman",
                subprocess.check_output(["pdffonts", "test.pdf"], text=True),
            )
        )
        == 1
    ), "font embedded once in multipage PDF"

    #########################

    for fname in ["test.pdf"] + [f"{i+1}.pnm" for i in range(num)]:
        if os.path.isfile(fname):
            os.remove(fname)
