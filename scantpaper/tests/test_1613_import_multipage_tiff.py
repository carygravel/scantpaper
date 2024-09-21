"Test importing TIFF"

import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(clean_up_files):
    "Test importing TIFF"

    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    subprocess.run(["tiffcp", "test.tif", "test.tif", "test2.tif"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=["test2.tif"],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert len(slist.data) == 2, "imported 2 pages"

    #########################

    clean_up_files(["test.tif", "test2.tif"])
