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

    path = "sed & awk.png"

    mlp = GLib.MainLoop()
    slist.save_image(
        path=path,
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", path], text=True)
    assert (
        re.search(rf"{path} PNG 70x46 70x46\+0\+0 8-bit sRGB", example) is not None
    ), "valid JPG created"

    #########################

    for fname in ["test.pnm", path]:
        if os.path.isfile(fname):
            os.remove(fname)
