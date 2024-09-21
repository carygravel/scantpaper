"Test analyse"

import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test analyse"

    subprocess.run(["convert", "xc:black", "black.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["black.pnm"])

    mlp = GLib.MainLoop()
    slist.analyse(
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert slist.data[0][2].mean == [0.0, 0.0, 0.0], "Found dark page"
    assert (
        os.path.dirname(slist.data[0][2].filename) == dirname.name
    ), "using session directory"

    #########################

    clean_up_files(["black.pnm"])
