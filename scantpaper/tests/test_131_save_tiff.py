"Test writing TIFF"

import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test writing TIFF"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    mlp = GLib.MainLoop()
    slist.save_tiff(
        path="test.tif",
        list_of_pages=[slist.data[0][2].uuid],
        options={
            "post_save_hook": "convert %i test2.png",
            "post_save_hook_options": "fg",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", "test.tif"], text=True)
    assert (
        re.search(r"test.tif TIFF 70x46 70x46\+0\+0 8-bit sRGB [.\d]+K?B", example)
        is not None
    ), "valid TIFF created"

    example = subprocess.check_output(["identify", "test2.png"], text=True)
    assert (
        re.search(
            r"test2\.png PNG 70x46 70x46\+0\+0 8-bit sRGB \d+\.?\d*K?B 0\.\d+u 0:00\.\d+\b",
            example,
        )
        is not None
    ), "ran post-save hook"

    #########################

    clean_up_files(["test.pnm", "test.tif", "test2.png"])
