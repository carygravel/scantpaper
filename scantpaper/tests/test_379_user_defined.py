"Test user-defined tools"

import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test user-defined tools"

    subprocess.run(["convert", "-size", "210x297", "xc:white", "white.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["white.pnm"])
    slist.data[0][2].resolution = (10, 10, "PixelsPerInch")

    mlp = GLib.MainLoop()
    slist.user_defined(
        page=slist.data[0][2],
        command="convert %i tmp.ppm;mv tmp.ppm %i",
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert slist.data[0][2].resolution == (
        10,
        10,
        "PixelsPerInch",
    ), "Resolution of converted image taken from input"

    #########################

    for fname in ["white.pnm"]:
        if os.path.isfile(fname):
            os.remove(fname)
