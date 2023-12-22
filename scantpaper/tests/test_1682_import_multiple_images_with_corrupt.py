"Test importing TIFF"

import os
import subprocess
import tempfile
import shutil
from gi.repository import GLib
from document import Document


def test_1():
    "Test importing TIFF"

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    subprocess.run(["convert", "rose:", "1.tif"], check=True)
    paths = ["1.tif"]
    for i in range(2, 11):
        paths.append(f"{i}.tif")
        if i != 5:
            shutil.copy2("1.tif", f"{i}.tif")

    # Create corrupt image
    subprocess.run(["touch", "5.tif"], check=True)

    mlp = GLib.MainLoop()

    asserts = 0

    def error_cb(response):
        nonlocal asserts
        assert (
            response.status == "Error importing zero-length file 5.tif."
        ), "caught error importing corrupt file"
        asserts += 1

    slist.import_files(
        paths=paths,
        error_callback=error_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert len(slist.data) == 9, "imported 9 pages"
    assert asserts == 1, "all callbacks run"

    #########################

    for fname in [f"{i}.tif" for i in range(1, 11)]:
        if os.path.isfile(fname):
            os.remove(fname)
