"Test writing TIFF with alpha layer"

import re
import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test writing TIFF with alpha layer"

    subprocess.run(
        [
            "convert",
            "-fill",
            "lightblue",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-units",
            "PixelsPerInch",
            "-density",
            "300",
            "label:The quick brown fox",
            "test.png",
        ],
        check=True,
    )

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.png"])

    mlp = GLib.MainLoop()
    slist.save_tiff(
        path="test.tif",
        list_of_pages=[slist.data[0][2]],
        options={
            "compression": "lzw",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", "test.tif"], text=True)
    assert (
        re.search(r"test.tif TIFF \d\d\dx\d\d \d\d\dx\d\d\+0\+0 16-bit sRGB", example)
        is not None
    ), "valid TIFF created"

    #########################

    for fname in ["test.png", "test.tif"]:
        if os.path.isfile(fname):
            os.remove(fname)
