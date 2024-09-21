"Test with non-English locale"

import re
import subprocess
import locale
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test with non-English locale"
    locale.setlocale(locale.LC_NUMERIC, "de_DE.utf8")

    # Create test image
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    # dir for temporary files
    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=mlp.quit,
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
    assert (
        re.search(r"Page size:\s+70 x 46 pts", capture) is not None
    ), "valid PDF created"

    #########################

    clean_up_files(["test.pnm", "test.pdf"])
