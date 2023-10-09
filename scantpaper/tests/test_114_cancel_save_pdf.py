"Test writing PDF with downsampled image"

import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test writing PDF with downsampled image"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    mlp = GLib.MainLoop()

    def finished_callback(_response):
        assert False, "Finished callback"

    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        finished_callback=finished_callback,
    )
    slist.cancel(lambda response: mlp.quit())
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    slist.save_image(
        path="test.jpg",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    assert subprocess.check_output(
        ["identify", "test.jpg"], text=True
    ), "can create a valid JPG after cancelling save PDF process"

    #########################

    for fname in ["test.pnm", "test.pdf", "test.jpg"]:
        if os.path.isfile(fname):
            os.remove(fname)
