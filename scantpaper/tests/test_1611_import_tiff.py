"Test importing TIFF"

import os
import pathlib
import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_import_tiff(rose_tif, temp_db, clean_up_files):
    "Test importing basic TIFF"
    slist = Document(db=temp_db.name)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=[rose_tif.name],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    page = slist.thread.get_page(id=1)
    assert page.image_object.mode == "RGB", "TIFF imported correctly"

    #########################

    clean_up_files(slist.thread.db_files)


def test_import_tiff_with_units(temp_tif, temp_db, clean_up_files):
    "Test importing TIFF with units"

    subprocess.run(
        [
            "convert",
            "rose:",
            "-units",
            "PixelsPerInch",
            "-density",
            "72x72",
            temp_tif.name,
        ],
        check=True,
    )

    slist = Document(db=temp_db.name)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=[temp_tif.name],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    page = slist.thread.get_page(id=1)
    assert page.image_object.mode == "RGB", "TIFF imported correctly"

    #########################

    clean_up_files(slist.thread.db_files)


def test_import_tiff_with_error(rose_tif, clean_up_files):
    "Test importing TIFF"
    with tempfile.TemporaryDirectory() as dirname:
        slist = Document(dir=dirname)

        mlp = GLib.MainLoop()

        asserts = 0

        # inject error during import file
        os.chmod(dirname, 0o500)  # allow access

        def error_cb(_page, _process, message):
            nonlocal asserts
            assert re.search(r"^Error", message), "error_cb"
            asserts += 1

            # inject error during import file
            os.chmod(dirname, 0o700)  # allow write access

        slist.import_files(
            paths=[rose_tif.name],
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
            os.chmod(dirname, 0o500)  # no write access

        slist.import_files(
            paths=[rose_tif.name],
            queued_callback=queued_cb,
            error_callback=error_cb,
            finished_callback=lambda response: mlp.quit(),
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        assert asserts == 3, "all callbacks run"

        #########################

        clean_up_files(slist.thread.db_files)


def test_import_multipage_tiff(rose_tif, temp_db, clean_up_files):
    "Test importing TIFF"
    with tempfile.NamedTemporaryFile(suffix=".tif") as temp_tif2:
        subprocess.run(
            ["tiffcp", rose_tif.name, rose_tif.name, temp_tif2.name], check=True
        )

        slist = Document(db=temp_db.name)

        mlp = GLib.MainLoop()

        slist.import_files(
            paths=[temp_tif2.name],
            finished_callback=lambda response: mlp.quit(),
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        assert len(slist.data) == 2, "imported 2 pages"

    clean_up_files(slist.thread.db_files)


def test_import_linked_tiff(rose_tif, temp_db, clean_up_files):
    "Test importing TIFF"
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_tif = pathlib.Path(temp_dir) / "test.tif"
        subprocess.run(["ln", "-s", rose_tif.name, temp_tif], check=True)
        subprocess.check_output(
            ["identify", "-format", "%m %G %g %z-bit %r", rose_tif.name], text=True
        )

        slist = Document(db=temp_db.name)

        mlp = GLib.MainLoop()

        slist.import_files(
            paths=[str(temp_tif)],
            finished_callback=lambda response: mlp.quit(),
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        page = slist.thread.get_page(id=1)
        assert page.image_object.mode == "RGB", "TIFF imported correctly"

    clean_up_files(slist.thread.db_files)


def test_import_multiple_tiffs_with_corrupt(temp_db, rose_tif, clean_up_files):
    "Test importing TIFF"

    slist = Document(db=temp_db.name)
    paths = [rose_tif.name for _ in range(9)]

    # insert a zero-length file
    subprocess.run(["touch", "5.tif"], check=True)
    paths.insert(4, "5.tif")

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

    clean_up_files(slist.thread.db_files + ["5.tif"])


def test_cancel_import_tiff(rose_tif, temp_db, import_in_mainloop, clean_up_files):
    "Test importing TIFF"
    subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", rose_tif.name], text=True
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
        paths=[rose_tif.name],
        finished_callback=finished_cb,
    )
    slist.cancel(cancelled_cb)

    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"

    import_in_mainloop(slist, [rose_tif.name])
    page = slist.thread.get_page(id=1)
    assert (
        page.image_object.mode == "RGB"
    ), "TIFF imported correctly after cancelling previous import"

    #########################

    clean_up_files(slist.thread.db_files)
