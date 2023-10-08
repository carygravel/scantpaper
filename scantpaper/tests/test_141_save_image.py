"Test writing PDF with downsampled image"

import re
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
    slist.save_image(
        path="test.jpg",
        list_of_pages=[slist.data[0][2]],
        options={
            "post_save_hook": "convert %i test2.png",
            "post_save_hook_options": "fg",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", "test.jpg"], text=True)
    assert (
        re.search(r"test.jpg JPEG 70x46 70x46\+0\+0 8-bit sRGB", example) is not None
    ), "valid JPG created"

    example = subprocess.check_output(["identify", "test2.png"], text=True)
    assert (
        re.search(
            r"test2\.png PNG 70x46 70x46\+0\+0 8-bit sRGB \d+\.?\d*K?B 0\.\d+u 0:00\.\d+\b",
            example,
        )
        is not None
    ), "ran post-save hook"

    #########################

    for fname in ["test.pnm','test.jpg','test2.png"]:
        if os.path.isfile(fname):
            os.remove(fname)
