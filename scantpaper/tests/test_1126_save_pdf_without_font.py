"Test writing PDF with non-existing font"

import os
import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test writing PDF with non-existing font"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()
    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.data[0][2].import_text("äöü")
    asserts = 0

    def error_callback(response):
        nonlocal asserts
        assert response.info == "Save file", "expected process"
        assert (
            response.status == "Unable to find font 'removed'. Defaulting to core font."
        ), "expected error message"
        asserts += 1

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        options={"options": {"font": "removed"}},
        error_callback=error_callback,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    out = subprocess.check_output(["pdftotext", "test.pdf", "-"], text=True)
    assert re.search(r"äöü", out) is not None, "PDF with expected text"
    assert asserts == 1, "ran all callbacks"

    #########################

    for fname in ["test.pnm", "test.pdf"]:
        if os.path.isfile(fname):
            os.remove(fname)
