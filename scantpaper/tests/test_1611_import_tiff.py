"Test importing TIFF"

import os
import re
import shutil
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_import_tiff(temp_db, clean_up_files):
    "Test importing basic TIFF"

    subprocess.run(["convert", "rose:", "test.tif"], check=True)

    slist = Document(db=temp_db.name)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=["test.tif"],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    page = slist.thread.get_page(id=1)
    assert page.image_object.mode == "RGB", "TIFF imported correctly"

    #########################

    clean_up_files(slist.thread.db_files + ["test.tif"])


def test_import_tiff_with_units(temp_db, clean_up_files):
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

    slist = Document(db=temp_db.name)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=["test.tif"],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    page = slist.thread.get_page(id=1)
    assert page.image_object.mode == "RGB", "TIFF imported correctly"

    #########################

    clean_up_files(slist.thread.db_files + ["test.tif"])


def test_import_tiff_with_error(clean_up_files):
    "Test importing TIFF"

    subprocess.run(["convert", "rose:", "test.tif"], check=True)

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist = Document(dir=dirname.name)

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

    clean_up_files(slist.thread.db_files + ["test.tif"])


def test_import_multipage_tiff(temp_db, clean_up_files):
    "Test importing TIFF"

    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    subprocess.run(["tiffcp", "test.tif", "test.tif", "test2.tif"], check=True)

    slist = Document(db=temp_db.name)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=["test2.tif"],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert len(slist.data) == 2, "imported 2 pages"

    #########################

    clean_up_files(slist.thread.db_files + ["test.tif", "test2.tif"])


def test_import_linked_tiff(temp_db, clean_up_files):
    "Test importing TIFF"

    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    subprocess.run(["ln", "-s", "test.tif", "test2.tif"], check=True)
    subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", "test.tif"], text=True
    )

    slist = Document(db=temp_db.name)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=["test2.tif"],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    page = slist.thread.get_page(id=1)
    assert page.image_object.mode == "RGB", "TIFF imported correctly"

    #########################

    clean_up_files(slist.thread.db_files + ["test.tif", "test2.tif"])


def test_import_multiple_tiffs_with_corrupt(temp_db, clean_up_files):
    "Test importing TIFF"

    slist = Document(db=temp_db.name)

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
    GLib.timeout_add(4000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert len(slist.data) == 9, "imported 9 pages"
    assert asserts == 1, "all callbacks run"

    #########################

    clean_up_files(slist.thread.db_files + [f"{i}.tif" for i in range(1, 11)])


def test_cancel_import_tiff(temp_db, import_in_mainloop, clean_up_files):
    "Test importing TIFF"

    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", "test.tif"], text=True
    )

    slist = Document(db=temp_db.name)

    mlp = GLib.MainLoop()

    asserts = 0

    def finished_cb(response):
        assert False, "TIFF not imported"
        mlp.quit()

    def cancelled_cb(response):
        nonlocal asserts
        assert len(slist.data) == 0, "TIFF not imported"
        asserts += 1
        mlp.quit()

    slist.import_files(
        paths=["test.tif"],
        finished_callback=finished_cb,
    )
    slist.cancel(cancelled_cb)

    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"

    import_in_mainloop(slist, ["test.tif"])
    page = slist.thread.get_page(id=1)
    assert (
        page.image_object.mode == "RGB"
    ), "TIFF imported correctly after cancelling previous import"

    #########################

    clean_up_files(slist.thread.db_files + ["test.tif"])
