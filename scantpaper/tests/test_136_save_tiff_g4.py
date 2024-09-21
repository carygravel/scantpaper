"Test writing TIFF with group 4 compression"

import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test writing TIFF with group 4 compression"

    subprocess.run(["convert", "rose:", "test.png"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.png"])

    mlp = GLib.MainLoop()
    slist.save_tiff(
        path="test.tif",
        list_of_pages=[slist.data[0][2].uuid],
        options={
            "compression": "g4",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", "test.tif"], text=True)
    assert (
        re.search(r"test.tif TIFF 70x46 70x46\+0\+0 1-bit Bilevel Gray", example)
        is not None
    ), "valid TIFF created"

    #########################

    clean_up_files(["test.png", "test.tif", "test2.png"])
