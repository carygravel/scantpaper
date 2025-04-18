"Test importing TIFF"

import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_import_tiff(clean_up_files):
    "Test importing basic TIFF"

    subprocess.run(["convert", "rose:", "test.tif"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=["test.tif"],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert slist.data[0][2].image_object.mode == "RGB", "TIFF imported correctly"

    #########################

    clean_up_files(["test.tif"])


def test_import_tiff_with_units(clean_up_files):
    "Test importing TIFF with units"

    subprocess.run(
        [
            "convert",
            "rose:",
            "-units",
            "PixelsPerInch",
            "-density",
            "72x72",
            "test.tif",
        ],
        check=True,
    )

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=["test.tif"],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert slist.data[0][2].image_object.mode == "RGB", "TIFF imported correctly"

    #########################

    clean_up_files(["test.tif"])
