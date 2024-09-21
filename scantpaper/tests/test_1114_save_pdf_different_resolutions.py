"test saving a PDF with different resolutions in the height and width directions"

import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "test saving a PDF with different resolutions in the height and width directions"

    # Create test image
    subprocess.run(["convert", "rose:", "-density", "100x200", "test.png"], check=True)

    slist = Document()

    # dir for temporary files
    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.png"])

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
    assert (
        re.search(r"Page size:\s+50.4 x 16.56 pts", capture) is not None
    ), "valid PDF created"

    #########################

    clean_up_files(["test.png", "test.pdf"])
