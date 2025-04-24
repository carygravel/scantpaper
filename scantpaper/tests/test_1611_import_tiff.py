"Test importing TIFF"

import os
import re
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


def test_import_tiff_with_error(clean_up_files):
    "Test importing TIFF"

    subprocess.run(["convert", "rose:", "test.tif"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    mlp = GLib.MainLoop()

    asserts = 0

    # inject error during import file
    os.chmod(dirname.name, 0o500)  # allow access

    def error_cb(_page, _process, message):
        nonlocal asserts
        assert re.search(r"^Error", message), "error_cb"
        asserts += 1

        # inject error during import file
        os.chmod(dirname.name, 0o700)  # allow write access

    slist.import_files(
        paths=["test.tif"],
        error_callback=error_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    def queued_cb(response):
        nonlocal asserts
        assert response.request.process == "get_file_info", "queued_cb"
        asserts += 1

        # inject error during import file
        os.chmod(dirname.name, 0o500)  # no write access

    slist.import_files(
        paths=["test.tif"],
        queued_callback=queued_cb,
        error_callback=error_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 3, "all callbacks run"

    #########################

    clean_up_files(["test.tif"])


def test_import_multipage_tiff(clean_up_files):
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


def test_import_linked_tiff(clean_up_files):
    "Test importing TIFF"

    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    subprocess.run(["ln", "-s", "test.tif", "test2.tif"], check=True)
    subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", "test.tif"], text=True
    )

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

    assert slist.data[0][2].image_object.mode == "RGB", "TIFF imported correctly"

    #########################

    clean_up_files(["test.tif", "test2.tif"])
