"Test writing image"

import re
import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test writing image"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    os.mkdir("te'st")

    mlp = GLib.MainLoop()
    slist.save_image(
        path="te'st/test.jpg",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", "te'st/test.jpg"], text=True)
    assert (
        re.search(r"test.jpg JPEG 70x46 70x46\+0\+0 8-bit sRGB", example) is not None
    ), "valid JPG created"

    #########################

    for fname in ["test.pnm", "te'st/test.jpg"]:
        if os.path.isfile(fname):
            os.remove(fname)
